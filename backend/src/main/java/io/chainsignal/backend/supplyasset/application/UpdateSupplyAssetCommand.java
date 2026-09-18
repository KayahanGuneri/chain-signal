package io.chainsignal.backend.supplyasset.application;

import java.util.Objects;

import io.chainsignal.backend.supplyasset.domain.SupplyAssetType;

public record UpdateSupplyAssetCommand(
        SupplyAssetType type,
        String name,
        String country,
        String city,
        double latitude,
        double longitude,
        int criticality) {

    public UpdateSupplyAssetCommand {
        Objects.requireNonNull(type, "Supply asset type must not be null");

        requireNonBlank(name, "Supply asset name must not be blank");
        requireNonBlank(country, "Supply asset country must not be blank");
        requireNonBlank(city, "Supply asset city must not be blank");

        if (!Double.isFinite(latitude) || latitude < -90.0 || latitude > 90.0) {
            throw new IllegalArgumentException(
                    "Supply asset latitude must be between -90.0 and 90.0");
        }

        if (!Double.isFinite(longitude) || longitude < -180.0 || longitude > 180.0) {
            throw new IllegalArgumentException(
                    "Supply asset longitude must be between -180.0 and 180.0");
        }

        if (criticality < 1 || criticality > 5) {
            throw new IllegalArgumentException(
                    "Supply asset criticality must be between 1 and 5");
        }
    }

    private static void requireNonBlank(String value, String message) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(message);
        }
    }
}
