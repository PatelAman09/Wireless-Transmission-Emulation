function [rx_payload, metrics] = professional_rf_emulator(tx_payload, cfgPath)
% Byte-level RF channel abstraction using config parameters

cfg = jsondecode(fileread(cfgPath));

% -------------------------------
% Defaults (safe)
% -------------------------------
if ~isfield(cfg, "snr_db"); cfg.snr_db = 30; end
if ~isfield(cfg, "channel_model"); cfg.channel_model = "AWGN"; end

% -------------------------------
% Map SNR + channel to BER
% (Abstract model, not waveform)
% -------------------------------
snr = cfg.snr_db;

switch upper(cfg.channel_model)
    case "RAYLEIGH"
        % Empirical BER approximation for QPSK Rayleigh
        ber = 0.5 * (1 - sqrt(snr / (snr + 2)));
    otherwise
        % AWGN approximation
        ber = 0.5 * erfc(sqrt(10^(snr/10)));
end

ber = max(min(ber, 0.5), 0);  % clamp

% -------------------------------
% Byte-preserving corruption
% -------------------------------
tx = uint8(tx_payload);
rx = tx;

nBits = numel(rx) * 8;
nErrors = round(ber * nBits);

if nErrors > 0
    idx = randperm(nBits, min(nErrors, nBits));
    for k = idx
        byte = ceil(k / 8);
        bit  = mod(k-1, 8);
        rx(byte) = bitxor(rx(byte), bitshift(1, bit));
    end
end

% -------------------------------
% Outputs
% -------------------------------
rx_payload = rx;
metrics.ber = ber;
metrics.channel = cfg.channel_model;
metrics.snr_db = cfg.snr_db;

end
