package main

import "testing"

func TestServiceName(t *testing.T) {
	if serviceName == "" {
		t.Fatal("service name must not be empty")
	}
}