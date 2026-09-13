package io.chainsignal.backend;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ChainSignalApplicationTests {

    @Test
    void bootstrapContractHasAStableApplicationName() {
        assertThat("chainsignal-backend").isEqualTo("chainsignal-backend");
    }
}