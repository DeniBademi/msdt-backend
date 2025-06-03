# Stage 1: Base build stage
FROM python:3.13-slim AS builder

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip

# Copy the requirements file first (better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim

RUN useradd -m -r appuser && \
   mkdir /app && \
   chown -R appuser /app

# Create virtual environment in production
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Set the working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SECRET_KEY_FILE=/run/secrets/django_secret_key

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Start the application using Gunicorn
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--chdir", "bnserver", "bnserver.wsgi:application"]
