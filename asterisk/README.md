# Asterisk Telephony Gateway for Hello Farmer

This directory contains the Asterisk 20 LTS telephony container setup with PJSIP and AudioSocket.

## Features
- **PJSIP Endpoints**: Preconfigured test extensions `1001` and `1002` for SIP softphones (Linphone, Zoiper, MicroSIP).
- **AudioSocket Integration**: When a call dials extension `8028` (or `100`), Asterisk executes `AudioSocket(${UNIQUEID},backend:9092)`.
- **Transcoding**: Translates G.711 (PCMU/PCMA) to raw 8 kHz signed linear PCM (`slin`) and streams bidirectional audio over TCP to the Python AudioSocket server.

## Softphone Credentials for Local Testing
- **SIP Server / Domain**: IP address of your host machine (or `127.0.0.1` / Docker host)
- **Port**: `5060` (UDP)
- **Extension 1**:
  - Username: `1001`
  - Password: `FarmerPass1001!`
- **Extension 2**:
  - Username: `1002`
  - Password: `FarmerPass1002!`
- **Dial**: `8028` to connect to Hello Farmer assistant.
