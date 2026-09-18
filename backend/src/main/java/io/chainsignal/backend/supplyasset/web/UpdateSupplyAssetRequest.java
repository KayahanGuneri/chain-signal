package io.chainsignal.backend.supplyasset.web;

import io.chainsignal.backend.supplyasset.application.UpdateSupplyAssetCommand;
import io.chainsignal.backend.supplyasset.domain.SupplyAssetType;

public record UpdateSupplyAssetRequest(
        SupplyAssetType type,
        String name,
        String country,
        String city,
        Double latitude,
        Double longitude,
        Integer criticality) {

    public UpdateSupplyAssetCommand toCommand() {
        return new UpdateSupplyAssetCommand(
                type,
                name,
                country,
                city,
                requirePresent(latitude, "Supply asset latitude is required"),
                requirePresent(longitude, "Supply asset longitude is required"),
                requirePresent(criticality, "Supply asset criticality is required"));
    }

    private static <T> T requirePresent(T value, String message) {
        if (value == null) {
            throw new IllegalArgumentException(message);
        }

        return value;
    }
}
