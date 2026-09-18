package io.chainsignal.backend.supplyasset.application;

public final class SupplyAssetNotFoundException extends RuntimeException {

    public SupplyAssetNotFoundException(long id) {
        super("Supply asset not found: " + id);
    }

    public SupplyAssetNotFoundException(String message) {
        super(message);
    }
}
