const { NodeSDK } = require('@opentelemetry/sdk-node');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { ZipkinExporter } = require('@opentelemetry/exporter-zipkin');

const zipkinExporter = new ZipkinExporter({
  url: 'http://zipkin:9411/api/v2/spans',
});

const sdk = new NodeSDK({
  traceExporter: zipkinExporter,
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
  ],
  serviceName: process.env.OTEL_SERVICE_NAME || 'vacaciones-service',
});

sdk.start();

console.log('OpenTelemetry initialized for vacaciones-service');
