# Container image for the Route Demand Assistant.
#
# One image, two homes: it runs as a normal web server locally and as an AWS
# Lambda function, with no Lambda-specific code in the app. The AWS Lambda Web
# Adapter (copied in below) is what makes that possible.

# Small official Python base, matching the 3.12 we develop and test against.
FROM python:3.12-slim

# AWS Lambda Web Adapter (pinned to v1.0.1, verified current).
# This drops a Lambda "extension" into the image. On Lambda it sits in front of
# our server and translates each invocation into an ordinary HTTP request, so a
# plain FastAPI/uvicorn app needs no Lambda handler. Locally it does nothing.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app

# Install runtime dependencies FIRST, as their own layer. Docker caches layers,
# so this expensive step is only re-run when requirements.txt changes - not on
# every code edit. This is the single biggest build-speed win.
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

# Now copy the application code (changes often, so it comes after the deps).
COPY app/ ./app/

# PYTHONPATH makes `import app` resolve. The adapter forwards to port 8080 by
# default, so the server listens there; the readiness probe uses our /ping.
ENV PYTHONPATH=/app \
    PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/ping

EXPOSE 8080

# Start the web server. uvicorn serves FastAPI on 8080; the adapter (on Lambda)
# forwards invocations here. Locally, this is just a normal server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
