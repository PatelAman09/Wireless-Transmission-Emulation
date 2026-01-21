function [rx_payload, metrics] = rf_emulator(tx_payload)
%RF_EMULATOR
% BPSK + Flat Rayleigh + AWGN (SISO)
% Hardened against config mismatches (doppler / doppler_shift)

    % ------------------------------------------------------------
    % Load channel configuration
    % ------------------------------------------------------------
    cfg = evalin('base', 'CHANNEL_CFG');

    % ------------------------------------------------------------
    % Normalize Doppler field (CRITICAL FIX)
    % ------------------------------------------------------------
    if isfield(cfg, 'doppler_shift')
        doppler = double(cfg.doppler_shift);
    else
        doppler = 0;
    end

    % ------------------------------------------------------------
    % SNR
    % ------------------------------------------------------------
    snr_db = double(cfg.snr_db);

    % ------------------------------------------------------------
    % Force uint8 payload
    % ------------------------------------------------------------
    tx_payload = uint8(tx_payload(:)');
    num_bytes = length(tx_payload);

    % ------------------------------------------------------------
    % Bytes → bits (MSB first, deterministic)
    % ------------------------------------------------------------
    tx_bits = zeros(num_bytes * 8, 1);
    for b = 1:num_bytes
        v = double(tx_payload(b));
        for k = 1:8
            tx_bits((b-1)*8 + k) = bitget(v, 9-k);
        end
    end
    required_bits = length(tx_bits);

    % ------------------------------------------------------------
    % BPSK modulation
    % ------------------------------------------------------------
    tx_symbols = 2*double(tx_bits) - 1;

    % ------------------------------------------------------------
    % Flat Rayleigh fading
    % ------------------------------------------------------------
    h = (randn(size(tx_symbols)) + 1j*randn(size(tx_symbols))) / sqrt(2);
    rx_symbols = h .* tx_symbols;

    % ------------------------------------------------------------
    % AWGN
    % ------------------------------------------------------------
    rx_symbols = awgn(rx_symbols, snr_db, 'measured');

    % ------------------------------------------------------------
    % Perfect equalization
    % ------------------------------------------------------------
    h(abs(h) < 1e-6) = 1;
    rx_symbols = rx_symbols ./ h;

    % ------------------------------------------------------------
    % BPSK hard decision
    % ------------------------------------------------------------
    rx_bits = real(rx_symbols) > 0;
    rx_bits = rx_bits(1:required_bits);

    % ------------------------------------------------------------
    % Bits → bytes (MSB first)
    % ------------------------------------------------------------
    rx_payload = zeros(1, num_bytes, 'uint8');
    for b = 1:num_bytes
        val = 0;
        for k = 1:8
            if rx_bits((b-1)*8 + k)
                val = bitset(val, 9-k);
            end
        end
        rx_payload(b) = uint8(val);
    end

    % ------------------------------------------------------------
    % Metrics (NO cfg.doppler reference)
    % ------------------------------------------------------------
    bit_errors  = sum(tx_bits ~= rx_bits);
    byte_errors = sum(tx_payload ~= rx_payload);

    metrics = struct();
    metrics.snr_db      = double(snr_db);
    metrics.doppler     = double(doppler);
    metrics.channel_model = 'flat_rayleigh_bpsk';
    metrics.bit_errors  = double(bit_errors);
    metrics.ber         = double(bit_errors / required_bits);
    metrics.byte_errors = double(byte_errors);
    metrics.bytes_total = double(num_bytes);

end
