FROM golang:1.27.1-alpine AS build
WORKDIR /src

COPY go.mod .
COPY cmd ./cmd

RUN go test ./...
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/replay-service ./cmd/replay

FROM scratch

COPY --from=build /out/replay-service /replay-service

ENTRYPOINT ["/replay-service"]