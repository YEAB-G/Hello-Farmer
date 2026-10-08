FROM alpine:3.19

RUN apk add --no-cache \
    asterisk \
    asterisk-sample-config \
    asterisk-sounds-en \
    asterisk-speex \
    asterisk-srtp \
    curl

# Copy custom configurations
COPY pjsip.conf /etc/asterisk/pjsip.conf
COPY extensions.conf /etc/asterisk/extensions.conf
COPY modules.conf /etc/asterisk/modules.conf

# Asterisk permissions
RUN chown -R asterisk:asterisk /etc/asterisk /var/spool/asterisk /var/log/asterisk /var/run/asterisk

EXPOSE 5060/udp
EXPOSE 5060/tcp
EXPOSE 10000-10020/udp

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD asterisk -rx "core show sysinfo" || exit 1

ENTRYPOINT ["asterisk", "-f", "-vvvg", "-c"]
