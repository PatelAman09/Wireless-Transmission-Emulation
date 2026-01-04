% Simple test to verify RF emulator basics

clear; clc;

fprintf('=== Simple RF Emulator Test ===\n\n');

% Load config
config_path = '../config/matlab_channel_config.json';
cfg = jsondecode(fileread(config_path));
init_channel(cfg);

fprintf('Config: SNR=%d dB, Doppler=%d Hz\n\n', cfg.snr_db, cfg.doppler_shift);

% Test different message lengths
test_cases = {
    'A'          % 1 byte
    'AB'         % 2 bytes
    'Hello'      % 5 bytes
    'Test123'    % 7 bytes
    'SimURF Demo' % 11 bytes
};

fprintf('Testing %d messages...\n', length(test_cases));
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

all_pass = true;

for i = 1:length(test_cases)
    msg = test_cases{i};
    tx = uint8(msg);
    
    fprintf('\nTest %d: "%s" (%d bytes)\n', i, msg, length(tx));
    fprintf('  TX: [%s]\n', num2str(tx(1:min(10, end))));
    
    try
        [rx, metrics] = rf_emulator(tx);
        
        % Validation checks
        if length(rx) ~= length(tx)
            fprintf('   LENGTH MISMATCH: %d → %d\n', length(tx), length(rx));
            all_pass = false;
            continue;
        end
        
        if any(rx > 255) || any(rx < 0)
            fprintf('  INVALID BYTE VALUES\n');
            all_pass = false;
            continue;
        end
        
        % Show results
        fprintf('  RX: [%s]\n', num2str(rx(1:min(10, end))));
        fprintf('  Received: "%s"\n', char(rx));
        fprintf('  Byte errors: %d/%d (%.1f%%)\n', metrics.byte_errors, metrics.bytes_total, ...
            100*metrics.byte_errors/metrics.bytes_total);
        fprintf('  BER: %.4f (%d/%d bits)\n', metrics.ber, metrics.bit_errors, metrics.bytes_total*8);
        fprintf('  ✓ PASS\n');
        
    catch ME
        fprintf('  ERROR: %s\n', ME.message);
        all_pass = false;
    end
end

fprintf('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

if all_pass
    fprintf('\n ALL TESTS PASSED!\n');
    fprintf(' RF emulator is working correctly\n');
    fprintf('\nNext: Run full simulation\n');
    fprintf('  1. docker-compose up -d --build\n');
    fprintf('  2. python simurf_matlab_bridge.py\n');
else
    fprintf('\n SOME TESTS FAILED\n');
    fprintf('Check rf_emulator.m for issues\n');
end