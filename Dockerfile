FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends git cmake g++ make libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch b11823 https://github.com/ggml-org/llama.cpp.git /src
RUN cmake -S /src -B /src/build -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DGGML_OPENMP=OFF -DBUILD_SHARED_LIBS=OFF && cmake --build /src/build --config Release -j 2 --target llama-server

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libstdc++6 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=build /src/build/bin/llama-server /usr/local/bin/llama-server
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt huggingface_hub
COPY --chown=app:app geoai /app/geoai
COPY --chown=app:app deployment /app/deployment
RUN mkdir -p /app/models /app/work && chown -R app:app /app
USER app
ENV HOME=/home/app PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["python", "deployment/serve.py"]
