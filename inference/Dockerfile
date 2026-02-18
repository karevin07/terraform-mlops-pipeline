# Build Stage
# Using latest to support go 1.25 requirement from go.mod
FROM golang:latest as builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o main .

# Final Stage
# Using Ubuntu 22.04 related to AWS Lambda provided environments (e.g. provided.al2023 or custom)
# Here using ubuntu for simplicity and glibc compatibility
FROM ubuntu:22.04

# Install dependencies for ONNX Runtime and basic utils
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Download ONNX Runtime Shared Library
# Using v1.20.0 which supports API level 20 (required by onnxruntime_go v1.17.0)
RUN curl -L -o /tmp/onnxruntime.tgz https://github.com/microsoft/onnxruntime/releases/download/v1.20.0/onnxruntime-linux-x64-1.20.0.tgz \
    && tar -xzf /tmp/onnxruntime.tgz -C /tmp \
    && mv /tmp/onnxruntime-linux-x64-1.20.0/lib/libonnxruntime.so.1.20.0 /usr/lib/libonnxruntime.so \
    && ln -s /usr/lib/libonnxruntime.so /usr/lib/libonnxruntime.so.1.20.0 \
    && rm -rf /tmp/onnxruntime*

# Set library path
ENV ONNXRUNTIME_LIB_PATH=/usr/lib/libonnxruntime.so
# Use simple assignment if LD_LIBRARY_PATH is not set in base
ENV LD_LIBRARY_PATH=/usr/lib

COPY --from=builder /app/main /main

# Entrypoint for Lambda (if using AWS Lambda Web Adapter or Custom Runtime)
# For native Go Lambda, we usually name it "bootstrap" if using provided.al2 or provided.al2023
# If using container image for Lambda, CMD ["/main"] works if configured in Terraform.
CMD ["/main"]
