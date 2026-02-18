package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
	"sync"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	ginadapter "github.com/awslabs/aws-lambda-go-api-proxy/gin"
	"github.com/gin-gonic/gin"
	ort "github.com/yalue/onnxruntime_go"
)

var (
	ginLambda    *ginadapter.GinLambda
	ginEngine    *gin.Engine
	s3Client     *s3.Client
	dynamoClient *dynamodb.Client
	modelCache   *ort.DynamicAdvancedSession
	modelVersion string
	modelMutex   sync.RWMutex
)

// Environment Variables
var (
	S3ModelBucket = os.Getenv("S3_MODEL_BUCKET")
	DynamoDBTable = os.Getenv("DYNAMODB_TABLE")
	Region        = os.Getenv("AWS_REGION")
	ModelName     = "stock-prediction"
)

type PredictRequest struct {
	Features []float32 `json:"features"`
}

type PredictResponse struct {
	PredictedPrice float32 `json:"predicted_price"`
	ModelVersion   string  `json:"model_version"`
}

func init() {
	// Initialize AWS Clients
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(Region))
	if err != nil {
		log.Fatalf("unable to load SDK config, %v", err)
	}

	s3Client = s3.NewFromConfig(cfg)
	dynamoClient = dynamodb.NewFromConfig(cfg)

	// Initialize ONNX Runtime
	// Note: You must set the shared library path before initializing the library.
	// In Lambda/Docker, we'll place it at a known location.
	libPath := os.Getenv("ONNXRUNTIME_LIB_PATH")
	if libPath == "" {
		libPath = "/var/task/libonnxruntime.so" // Default for Lambda
	}

	// Only initialize if library exists (to avoid panic on local dev without lib)
	if _, err := os.Stat(libPath); err == nil {
		ort.SetSharedLibraryPath(libPath)
		err = ort.InitializeEnvironment()
		if err != nil {
			log.Printf("Warning: Failed to initialize ONNX environment: %v", err)
		}
	} else {
		log.Printf("Warning: ONNX library not found at %s", libPath)
	}

	// Setup Gin
	r := gin.Default()
	r.GET("/health", healthHandler)
	r.POST("/predict", predictHandler)

	ginEngine = r
	ginLambda = ginadapter.New(r)
}

func healthHandler(c *gin.Context) {
	c.JSON(200, gin.H{"status": "ok"})
}

func predictHandler(c *gin.Context) {
	var req PredictRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": "Invalid request body"})
		return
	}

	if len(req.Features) != 4 {
		c.JSON(400, gin.H{"error": "Expected 4 features"})
		return
	}

	// Load model if not cached
	if err := ensureModelLoaded(context.Background()); err != nil {
		log.Printf("Model load failed: %v", err)
		c.JSON(503, gin.H{"error": "Service unavailable"})
		return
	}

	modelMutex.RLock()
	session := modelCache
	version := modelVersion
	modelMutex.RUnlock()

	if session == nil {
		c.JSON(500, gin.H{"error": "Model not loaded"})
		return
	}

	// Prepare input tensor
	// Shape: [1, 4]
	inputData := req.Features
	inputTensor, err := ort.NewTensor(ort.NewShape(1, 4), inputData)
	if err != nil {
		log.Printf("Failed to create input tensor: %v", err)
		c.JSON(500, gin.H{"error": "Inference error"})
		return
	}
	defer inputTensor.Destroy()

	// Run Inference
	// We matched names "float_input" and "variable" in ensureModelLoaded via creating session with them.
	// DynamicAdvancedSession.Run takes inputs and outputs.

	// Prepare Output Tensor [1, 1]
	outputData := make([]float32, 1) // buffer for output
	outputTensor, err := ort.NewTensor(ort.NewShape(1, 1), outputData)
	if err != nil {
		log.Printf("Failed to create output tensor: %v", err)
		c.JSON(500, gin.H{"error": "Inference setup failed"})
		return
	}
	defer outputTensor.Destroy()

	err = session.Run(
		[]ort.Value{inputTensor},
		[]ort.Value{outputTensor},
	)
	if err != nil {
		log.Printf("Inference execution failed: %v", err)
		c.JSON(500, gin.H{"error": "Inference execution failed"})
		return
	}

	// Get Output Data
	// outputData is already populated?
	// ort.Tensor stores pointer to data. If we created it from slice, does it write back?
	// Yes, NewTensor uses the slice as backing if possible, or copies.
	// Verify: yalue/onnxruntime_go: "The Go slice passed to NewTensor must remain allocated..."
	// It says "The data is NOT copied...". So correct.
	prediction := outputData[0]

	c.JSON(200, PredictResponse{
		PredictedPrice: prediction,
		ModelVersion:   version,
	})
}

func ensureModelLoaded(ctx context.Context) error {
	modelMutex.RLock()
	if modelCache != nil {
		modelMutex.RUnlock()
		return nil
	}
	modelMutex.RUnlock()

	modelMutex.Lock()
	defer modelMutex.Unlock()

	// Double check
	if modelCache != nil {
		return nil
	}

	// Local Development Override
	if localPath := os.Getenv("LOCAL_MODEL_PATH"); localPath != "" {
		log.Printf("Loading model from local path: %s", localPath)
		inputNames := []string{"float_input"}
		outputNames := []string{"variable"}
		session, err := ort.NewDynamicAdvancedSession(localPath, inputNames, outputNames, nil)
		if err != nil {
			return fmt.Errorf("failed to create local onnx session: %w", err)
		}
		modelCache = session
		modelVersion = "local"
		return nil
	}

	// 1. Get latest stable version from DynamoDB
	// Query: ModelName = :name, Filter: Status = stable OR canary
	// Using Query on GSI or standard Query if PK is ModelName
	// infra/modules/dynamodb/main.tf shows schema.
	// Usually PK=ModelName, SK=Version

	// We'll mimic Python logic: Query latest, verify status
	// Note: Assuming PK=ModelName, SK=Version (Sort desc)
	out, err := dynamoClient.Query(ctx, &dynamodb.QueryInput{
		TableName:              aws.String(DynamoDBTable),
		KeyConditionExpression: aws.String("ModelName = :name"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":name": &types.AttributeValueMemberS{Value: ModelName},
		},
		ScanIndexForward: aws.Bool(false), // Descending
		Limit:            aws.Int32(5),
	})
	if err != nil {
		return fmt.Errorf("failed to query dynamodb: %w", err)
	}

	var targetItem map[string]types.AttributeValue
	for _, item := range out.Items {
		status := ""
		if v, ok := item["Status"].(*types.AttributeValueMemberS); ok {
			status = v.Value
		}
		if status == "stable" || status == "canary" {
			targetItem = item
			break
		}
	}

	if targetItem == nil {
		return fmt.Errorf("no stable model found")
	}

	// get OnnxUrl
	var onnxUrl string
	if v, ok := targetItem["OnnxUrl"].(*types.AttributeValueMemberS); ok {
		onnxUrl = v.Value
	} else {
		// Fallback or Try ArtifactUrl if .onnx?
		// Let's check ArtifactUrl
		if _, ok := targetItem["ArtifactUrl"].(*types.AttributeValueMemberS); ok {
			// If python didn't set OnnxUrl yet, we might fail.
			// But we updated python code.
			// If running against OLD records, this will fail.
			return fmt.Errorf("model OnnxUrl not found")
		}
	}

	version := ""
	if v, ok := targetItem["Version"].(*types.AttributeValueMemberS); ok {
		version = v.Value
	}

	// 2. Download from S3
	bucket := S3ModelBucket
	key := strings.Replace(onnxUrl, fmt.Sprintf("s3://%s/", bucket), "", 1)

	log.Printf("Downloading model from s3://%s/%s", bucket, key)

	tmpFile := "/tmp/model.onnx"
	file, err := os.Create(tmpFile)
	if err != nil {
		return fmt.Errorf("failed to create temp file: %w", err)
	}
	defer file.Close()

	resp, err := s3Client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("failed to download from s3: %w", err)
	}
	defer resp.Body.Close()

	_, err = io.Copy(file, resp.Body)
	if err != nil {
		return fmt.Errorf("failed to write model file: %w", err)
	}

	// 3. Load ONNX Session
	// Define input/output names matching skl2onnx export (`training/train.py`)
	inputNames := []string{"float_input"}
	outputNames := []string{"variable"}

	session, err := ort.NewDynamicAdvancedSession(
		tmpFile,
		inputNames,
		outputNames,
		nil,
	)
	if err != nil {
		return fmt.Errorf("failed to create onnx session: %w", err)
	}

	modelCache = session
	modelVersion = version
	return nil
}

func Handler(ctx context.Context, req events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	return ginLambda.ProxyWithContext(ctx, req)
}

func main() {
	if os.Getenv("AWS_LAMBDA_FUNCTION_NAME") != "" {
		lambda.Start(Handler)
	} else {
		// Local Run
		log.Println("Starting local server on :8080")
		ginEngine.Run(":8080")
	}
}
