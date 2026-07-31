package main

import "testing"

func TestSelectLane_BothPresent(t *testing.T) {
	stable := &RegistryModel{Version: "v1", OnnxURL: "s3://b/v1.onnx", Status: "stable"}
	canary := &RegistryModel{Version: "v2", OnnxURL: "s3://b/v2.onnx", Status: "canary"}

	got := SelectLane(stable, canary, 0) // 0% canary → always stable
	if got.Version != "v1" || got.Lane != "stable" {
		t.Fatalf("expected stable v1, got %+v", got)
	}

	got = SelectLane(stable, canary, 100) // 100% canary
	if got.Version != "v2" || got.Lane != "canary" {
		t.Fatalf("expected canary v2, got %+v", got)
	}
}

func TestSelectLane_OnlyCanary(t *testing.T) {
	canary := &RegistryModel{Version: "v2", OnnxURL: "s3://b/v2.onnx", Status: "canary"}
	got := SelectLane(nil, canary, 10)
	if got == nil || got.Version != "v2" {
		t.Fatalf("expected canary only, got %+v", got)
	}
}

func TestSelectLane_Neither(t *testing.T) {
	if SelectLane(nil, nil, 10) != nil {
		t.Fatal("expected nil")
	}
}

func TestLatestStableAndCanary(t *testing.T) {
	items := []RegistryModel{
		{Version: "v3", Status: "staging"},
		{Version: "v2", Status: "canary", OnnxURL: "s3://b/v2.onnx"},
		{Version: "v1", Status: "stable", OnnxURL: "s3://b/v1.onnx"},
	}
	stable, canary := LatestStableAndCanary(items)
	if stable == nil || stable.Version != "v1" {
		t.Fatalf("stable=%+v", stable)
	}
	if canary == nil || canary.Version != "v2" {
		t.Fatalf("canary=%+v", canary)
	}
}
