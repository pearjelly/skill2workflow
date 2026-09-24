FROM python:3.14-slim-bookworm AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY web ./web
COPY examples/control-plane-snapshot.json ./examples/control-plane-snapshot.json
COPY examples/workflows ./examples/workflows
RUN python -m pip install --no-cache-dir "setuptools>=77.0.1" \
    && python -m pip wheel --no-deps --no-build-isolation --wheel-dir /wheelhouse .

FROM python:3.14-slim-bookworm

RUN groupadd --system --gid 65532 skill2workflow \
    && useradd --system --uid 65532 --gid 65532 \
       --home-dir /nonexistent --shell /usr/sbin/nologin skill2workflow \
    && mkdir -p /srv/skill2workflow/team-a
COPY --from=builder /wheelhouse /wheelhouse
RUN python -m pip install --no-cache-dir --no-index --no-deps /wheelhouse/skill2workflow-*.whl \
    && rm -rf /wheelhouse

USER 65532:65532
ENTRYPOINT ["skill2workflow"]
CMD ["service", "--config", "/srv/skill2workflow/team-a/config/service.json"]
