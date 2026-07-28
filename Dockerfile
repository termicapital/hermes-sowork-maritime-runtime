FROM nousresearch/hermes-agent@sha256:d887ef6e9ee71f9f3700d23a01816ae38ac5b74436a6c21937a7fd37fdfd9a35

USER root
COPY discovery_runtime.py /opt/discovery-runtime/discovery_runtime.py
COPY openrouter_safe_tool.py /opt/hermes/tools/openrouter_safe_tool.py
COPY install_readonly_toolset.py /opt/discovery-runtime/install_readonly_toolset.py
COPY --chmod=0755 entrypoint.sh /opt/discovery-runtime/entrypoint.sh
COPY --chmod=0755 verify-runtime.sh /opt/discovery-runtime/verify-runtime.sh
RUN /opt/hermes/.venv/bin/python /opt/discovery-runtime/install_readonly_toolset.py /opt/hermes/toolsets.py

ENV HOME=/data/hermes
ENV HERMES_HOME=/data/hermes
ENV HERMES_WRITE_SAFE_ROOT=/data/hermes/discovery-scout
ENV PATH=/opt/hermes/.venv/bin:/data/hermes/bin:/data/hermes/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV HERMES_CMD=/opt/hermes/.venv/bin/hermes
ENV PORT=8765

WORKDIR /opt/discovery-runtime
USER root
EXPOSE 8765
ENTRYPOINT ["/opt/discovery-runtime/entrypoint.sh"]
