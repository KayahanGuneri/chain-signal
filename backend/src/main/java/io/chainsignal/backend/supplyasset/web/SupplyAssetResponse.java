package io.chainsignal.backend.supplyasset.web;

import io.chainsignal.backend.supplyasset.domain.SupplyAsset;
import io.chainsignal.backend.supplyasset.domain.SupplyAssetType;

public record SupplyAssetResponse(
        long id,
        SupplyAssetType type,
        String name,
        String country,
        String city,
        double latitude,
        double longitude,
        int criticality,
        boolean active) {

    public static SupplyAssetResponse from(SupplyAsset asset) {
        return new SupplyAssetResponse(
                asset.id(),
                asset.type(),
                asset.name(),
                asset.country(),
                asset.city(),
                asset.latitude(),
                asset.longitude(),
                asset.criticality(),
                asset.active());
    }
}
