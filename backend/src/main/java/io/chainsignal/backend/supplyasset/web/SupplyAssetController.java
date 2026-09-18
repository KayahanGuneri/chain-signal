package io.chainsignal.backend.supplyasset.web;

import java.net.URI;
import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.chainsignal.backend.supplyasset.application.SupplyAssetService;

@RestController
@RequestMapping("/api/supply-assets")
public class SupplyAssetController {

    private final SupplyAssetService service;

    public SupplyAssetController(SupplyAssetService service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<SupplyAssetResponse> create(
            @RequestBody CreateSupplyAssetRequest request) {
        SupplyAssetResponse response = SupplyAssetResponse.from(
                service.create(request.toCommand()));

        return ResponseEntity
                .created(URI.create("/api/supply-assets/" + response.id()))
                .body(response);
    }

    @GetMapping("/{id}")
    public SupplyAssetResponse getById(@PathVariable long id) {
        return SupplyAssetResponse.from(service.getById(id));
    }

    @GetMapping
    public List<SupplyAssetResponse> list() {
        return service.list()
                .stream()
                .map(SupplyAssetResponse::from)
                .toList();
    }

    @PutMapping("/{id}")
    public SupplyAssetResponse update(
            @PathVariable long id,
            @RequestBody UpdateSupplyAssetRequest request) {
        return SupplyAssetResponse.from(
                service.update(id, request.toCommand()));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deactivate(@PathVariable long id) {
        service.deactivate(id);

        return ResponseEntity.noContent().build();
    }
}
