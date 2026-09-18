package io.chainsignal.backend.supplyasset.persistence;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import io.chainsignal.backend.supplyasset.application.CreateSupplyAssetCommand;
import io.chainsignal.backend.supplyasset.application.SupplyAssetRepository;
import io.chainsignal.backend.supplyasset.application.UpdateSupplyAssetCommand;
import io.chainsignal.backend.supplyasset.domain.SupplyAsset;
import io.chainsignal.backend.supplyasset.domain.SupplyAssetType;

@Repository
public class JdbcSupplyAssetRepository implements SupplyAssetRepository {

    private static final String CREATE_SQL = """
            INSERT INTO supply_asset (
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality
            )
            VALUES (
                :type,
                :name,
                :country,
                :city,
                :latitude,
                :longitude,
                :criticality
            )
            RETURNING
                id,
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality,
                active
            """;

    private static final String FIND_BY_ID_SQL = """
            SELECT
                id,
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality,
                active
            FROM supply_asset
            WHERE id = :id
            """;

    private static final String FIND_ALL_SQL = """
            SELECT
                id,
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality,
                active
            FROM supply_asset
            ORDER BY id
            """;

    private static final String UPDATE_SQL = """
            UPDATE supply_asset
            SET
                type = :type,
                name = :name,
                country = :country,
                city = :city,
                latitude = :latitude,
                longitude = :longitude,
                criticality = :criticality
            WHERE id = :id
            RETURNING
                id,
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality,
                active
            """;

    private static final String DEACTIVATE_SQL = """
            UPDATE supply_asset
            SET active = FALSE
            WHERE id = :id
            RETURNING
                id,
                type,
                name,
                country,
                city,
                latitude,
                longitude,
                criticality,
                active
            """;

    private final JdbcClient jdbcClient;

    public JdbcSupplyAssetRepository(JdbcClient jdbcClient) {
        this.jdbcClient = jdbcClient;
    }

    @Override
    public SupplyAsset create(CreateSupplyAssetCommand command) {
        return jdbcClient.sql(CREATE_SQL)
                .param("type", command.type().name())
                .param("name", command.name())
                .param("country", command.country())
                .param("city", command.city())
                .param("latitude", command.latitude())
                .param("longitude", command.longitude())
                .param("criticality", command.criticality())
                .query(JdbcSupplyAssetRepository::mapRow)
                .single();
    }

    @Override
    public Optional<SupplyAsset> findById(long id) {
        return jdbcClient.sql(FIND_BY_ID_SQL)
                .param("id", id)
                .query(JdbcSupplyAssetRepository::mapRow)
                .optional();
    }

    @Override
    public List<SupplyAsset> findAll() {
        return jdbcClient.sql(FIND_ALL_SQL)
                .query(JdbcSupplyAssetRepository::mapRow)
                .list();
    }

    @Override
    public Optional<SupplyAsset> update(
            long id,
            UpdateSupplyAssetCommand command) {
        return jdbcClient.sql(UPDATE_SQL)
                .param("id", id)
                .param("type", command.type().name())
                .param("name", command.name())
                .param("country", command.country())
                .param("city", command.city())
                .param("latitude", command.latitude())
                .param("longitude", command.longitude())
                .param("criticality", command.criticality())
                .query(JdbcSupplyAssetRepository::mapRow)
                .optional();
    }

    @Override
    public Optional<SupplyAsset> deactivate(long id) {
        return jdbcClient.sql(DEACTIVATE_SQL)
                .param("id", id)
                .query(JdbcSupplyAssetRepository::mapRow)
                .optional();
    }

    private static SupplyAsset mapRow(
            ResultSet resultSet,
            int rowNumber) throws SQLException {
        return new SupplyAsset(
                resultSet.getLong("id"),
                SupplyAssetType.valueOf(resultSet.getString("type")),
                resultSet.getString("name"),
                resultSet.getString("country"),
                resultSet.getString("city"),
                resultSet.getDouble("latitude"),
                resultSet.getDouble("longitude"),
                resultSet.getInt("criticality"),
                resultSet.getBoolean("active"));
    }
}
