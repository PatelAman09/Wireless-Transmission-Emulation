% quick_test.m - Quick verification of rf_emulator

clear; clc;

fprintf('=== Quick RF Emulator Test ===\n\n');

% Load config
config_path = '../config/matlab_channel_config.json';
cfg = jsondecode(fileread(config_path));
init_channel(cfg);

fprintf('Config: SNR=%d dB, Doppler=%d Hz\n\n', cfg.snr_db, cfg.doppler_shift);

% Simple test
msg = 'Hello';
tx = uint8(msg);

fprintf('Testing with: "%s"\n', msg);
fprintf('TX bytes: [%s]\n', num2str(tx));

[rx, metrics] = rf_emulator(tx);

fprintf('RX bytes: [%s]\n', num2str(rx));
fprintf('RX string: "%s"\n\n', char(rx));

% Check metrics
fprintf('Metrics:\n');
fprintf('  BER: %.4f (%.1f%%)\n', metrics.ber, metrics.ber*100);
fprintf('  Bit errors: %d / %d\n', metrics.bit_errors, length(tx)*8);
fprintf('  Byte errors: %d / %d\n', metrics.byte_errors, metrics.bytes_total);
fprintf('  Type check:\n');
fprintf('    bit_errors type: %s\n', class(metrics.bit_errors));
fprintf('    byte_errors type: %s\n', class(metrics.byte_errors));
fprintf('    ber type: %s\n', class(metrics.ber));

% Validation
fprintf('\n=== Validation ===\n');

if metrics.ber >= 1.0
    fprintf('❌ CRITICAL: BER = 100%% (all bits flipped)\n');
    fprintf('   This means the RF emulator is completely broken!\n');
elseif metrics.ber > 0.05
    fprintf('❌ BER too high (%.1f%%) - reduce to < 5%%\n', metrics.ber*100);
    fprintf('   Increase SNR or reduce multipath\n');
elseif metrics.ber > 0.03
    fprintf('⚠️  BER marginal (%.1f%%) - FEC may struggle\n', metrics.ber*100);
else
    fprintf('✅ BER good (%.1f%%) - FEC should work well\n', metrics.ber*100);
end

if ~isscalar(metrics.byte_errors)
    fprintf('❌ byte_errors is not scalar: %s\n', mat2str(size(metrics.byte_errors)));
else
    fprintf('✅ byte_errors is scalar\n');
end

if length(rx) == length(tx)
    fprintf('✅ Length preserved\n');
else
    fprintf('❌ Length changed: %d → %d\n', length(tx), length(rx));
end