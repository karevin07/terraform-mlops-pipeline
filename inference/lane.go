package main

import (
	"math/rand"
	"os"
	"strconv"
)

type RegistryModel struct {
	Version string
	OnnxURL string
	Status  string
}

type ServingChoice struct {
	Version string
	OnnxURL string
	Lane    string // "stable" | "canary"
}

func CanaryTrafficPercent() int {
	v := os.Getenv("CANARY_TRAFFIC_PERCENT")
	if v == "" {
		return 10
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 0 {
		return 10
	}
	if n > 100 {
		return 100
	}
	return n
}

// SelectLane chooses stable vs canary. percent is 0–100 canary probability when both exist.
func SelectLane(stable, canary *RegistryModel, canaryPercent int) *ServingChoice {
	if stable == nil && canary == nil {
		return nil
	}
	if canary == nil {
		return &ServingChoice{Version: stable.Version, OnnxURL: stable.OnnxURL, Lane: "stable"}
	}
	if stable == nil {
		return &ServingChoice{Version: canary.Version, OnnxURL: canary.OnnxURL, Lane: "canary"}
	}
	if canaryPercent >= 100 || (canaryPercent > 0 && rand.Intn(100) < canaryPercent) {
		return &ServingChoice{Version: canary.Version, OnnxURL: canary.OnnxURL, Lane: "canary"}
	}
	return &ServingChoice{Version: stable.Version, OnnxURL: stable.OnnxURL, Lane: "stable"}
}

// LatestStableAndCanary scans items already sorted newest-first.
func LatestStableAndCanary(items []RegistryModel) (stable, canary *RegistryModel) {
	for i := range items {
		it := &items[i]
		switch it.Status {
		case "stable":
			if stable == nil {
				stable = it
			}
		case "canary":
			if canary == nil {
				canary = it
			}
		}
		if stable != nil && canary != nil {
			break
		}
	}
	return stable, canary
}
