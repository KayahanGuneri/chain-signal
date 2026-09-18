package io.chainsignal.backend.supplyasset.web;

import java.time.Instant;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import io.chainsignal.backend.supplyasset.application.SupplyAssetNotFoundException;
import jakarta.servlet.http.HttpServletRequest;

@RestControllerAdvice
public class SupplyAssetExceptionHandler {

    @ExceptionHandler(SupplyAssetNotFoundException.class)
    public ResponseEntity<ApiErrorResponse> handleNotFound(
            SupplyAssetNotFoundException exception,
            HttpServletRequest request) {
        return errorResponse(
                HttpStatus.NOT_FOUND,
                exception.getMessage(),
                request.getRequestURI());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiErrorResponse> handleInvalidArgument(
            IllegalArgumentException exception,
            HttpServletRequest request) {
        return errorResponse(
                HttpStatus.BAD_REQUEST,
                exception.getMessage(),
                request.getRequestURI());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiErrorResponse> handleMalformedRequest(
            HttpMessageNotReadableException exception,
            HttpServletRequest request) {
        return errorResponse(
                HttpStatus.BAD_REQUEST,
                "Malformed request body",
                request.getRequestURI());
    }

    private static ResponseEntity<ApiErrorResponse> errorResponse(
            HttpStatus status,
            String message,
            String path) {
        return ResponseEntity
                .status(status)
                .body(
                        new ApiErrorResponse(
                                Instant.now(),
                                status.value(),
                                status.getReasonPhrase(),
                                message,
                                path));
    }
}
