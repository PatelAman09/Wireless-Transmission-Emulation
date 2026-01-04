% Comprehensive test of RF channel emulator with statistics

clear; clc; close all;

fprintf('╔════════════════════════════════════════════════╗\n');
fprintf('║   SimURF RF Channel Comprehensive Test        ║\n');
fprintf('╚════════════════════════════════════════════════╝\n\n');

% Add path to MATLAB components
addpath(pwd);

% Load configuration
config_path = '../config/matlab_channel_config.json';
if ~isfile(config_path)
    error('Config file not found: %s', config_path);
end

json_text = fileread(config_path);
cfg = jsondecode(json_text);

fprintf(' Channel Configuration:\n');
fprintf('   SNR: %d dB\n', cfg.snr_db);
fprintf('   Doppler Shift: %d Hz\n', cfg.doppler_shift);
fprintf('   Channel Model: %s\n', cfg.channel_model);
fprintf('   Multipath Delays: [%s] ns\n', num2str(cfg.multipath_delays));
fprintf('   Multipath Gains: [%s]\n', num2str(cfg.multipath_gains));
fprintf('   FEC Enabled: %d\n\n', cfg.use_fec);

% Initialize channel
init_channel(cfg);
fprintf(' Channel initialized\n\n');

% ============================================================
% Test 1: Single Short Message
% ============================================================
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
fprintf('TEST 1: Short Message\n');
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

msg = 'Hello';
tx_bytes = uint8(msg);

fprintf('Original: "%s"\n', msg);
fprintf('TX bytes: [%s]\n', num2str(tx_bytes));

try
    [rx_bytes, metrics] = rf_emulator(tx_bytes);
    
    rx_msg = char(rx_bytes);
    fprintf('RX bytes: [%s]\n', num2str(rx_bytes));
    fprintf('Received: "%s"\n', rx_msg);
    
    % FIXED: Ensure scalar comparison
    byte_errors = sum(tx_bytes(:) ~= rx_bytes(:));
    fprintf('Byte errors: %d/%d (%.1f%%)\n', byte_errors, length(tx_bytes), 100*byte_errors/length(tx_bytes));
    fprintf('Bit errors: %d/%d (BER=%.4f)\n\n', metrics.bit_errors, length(tx_bytes)*8, metrics.ber);
catch ME
    fprintf(' ERROR: %s\n\n', ME.message);
end

% ============================================================
% Test 2: Multiple Messages - Statistics
% ============================================================
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
fprintf('TEST 2: Multiple Messages (Statistics)\n');
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

test_messages = {
    'A'
    'Hi'
    'Test'
    'Hello'
    'SimURF'
    'Wireless'
    'Transmission'
    'Hello World!'
    'RF Channel Test'
    'QPSK Modulation Demo'
};

total_byte_errors = 0;
total_bytes = 0;
total_bit_errors = 0;
total_bits = 0;

fprintf('Running %d tests...\n\n', length(test_messages));

for i = 1:length(test_messages)
    msg = test_messages{i};
    tx = uint8(msg);
    
    try
        [rx, met] = rf_emulator(tx);
        
        % FIXED: Force vectors and ensure scalar sum
        tx_vec = tx(:);
        rx_vec = rx(:);
        
        % Ensure same length for comparison
        if length(rx_vec) ~= length(tx_vec)
            fprintf('%2d. "%s" → ERROR: Length mismatch (%d→%d)\n', ...
                i, msg, length(tx_vec), length(rx_vec));
            continue;
        end
        
        byte_err = sum(tx_vec ~= rx_vec);  % This is now guaranteed scalar
        
        total_byte_errors = total_byte_errors + byte_err;
        total_bytes = total_bytes + length(tx_vec);
        total_bit_errors = total_bit_errors + met.bit_errors;
        total_bits = total_bits + length(tx_vec) * 8;
        
        fprintf('%2d. "%s" → "%s" | Byte errors: %d/%d', ...
            i, msg, char(rx), byte_err, length(tx));
        
        if byte_err == 0
            fprintf(' ✓\n');
        else
            fprintf('\n');
        end
        
    catch ME
        fprintf('%2d. "%s" → ERROR: %s\n', i, msg, ME.message);
    end
end

fprintf('\n Aggregate Statistics:\n');
fprintf('   Total bytes: %d\n', total_bytes);
fprintf('   Byte errors: %d (%.2f%%)\n', total_byte_errors, 100*total_byte_errors/total_bytes);
fprintf('   Total bits: %d\n', total_bits);
fprintf('   Bit errors: %d (BER=%.4f)\n', total_bit_errors, total_bit_errors/total_bits);

% ============================================================
% Test 3: Error Distribution
% ============================================================
fprintf('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
fprintf('TEST 3: Error Distribution (100 packets)\n');
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

num_trials = 100;
ber_samples = zeros(num_trials, 1);
test_msg = 'TestPacket';

fprintf('Transmitting %d packets of "%s"...\n', num_trials, test_msg);

success_count = 0;
for i = 1:num_trials
    try
        tx = uint8(test_msg);
        [~, met] = rf_emulator(tx);
        ber_samples(i) = met.ber;
        success_count = success_count + 1;
    catch ME
        fprintf('Trial %d failed: %s\n', i, ME.message);
        ber_samples(i) = NaN;
    end
    
    if mod(i, 20) == 0
        fprintf('  Completed %d/%d trials...\n', i, num_trials);
    end
end

% Remove failed trials
ber_samples = ber_samples(~isnan(ber_samples));

fprintf('\n BER Statistics (%d successful trials):\n', success_count);
fprintf('   Mean BER: %.4f\n', mean(ber_samples));
fprintf('   Std BER:  %.4f\n', std(ber_samples));
fprintf('   Min BER:  %.4f\n', min(ber_samples));
fprintf('   Max BER:  %.4f\n', max(ber_samples));

% Plot BER distribution
figure('Name', 'BER Distribution');
histogram(ber_samples, 20);
xlabel('Bit Error Rate (BER)');
ylabel('Count');
title(sprintf('BER Distribution over %d Packets', success_count));
grid on;

% ============================================================
% Test 4: Validation Checks
% ============================================================
fprintf('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
fprintf('TEST 4: Validation Checks\n');
fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

validation_pass = true;

% Check 1: Length preservation
test_lens = [1, 5, 10, 20, 50, 100];
fprintf(' Length preservation test:\n');
for len = test_lens
    try
        tx = uint8(randi([0, 255], 1, len));
        rx = rf_emulator(tx);
        if length(rx) == len
            fprintf('  %3d bytes: ✓ OK\n', len);
        else
            fprintf('  %3d bytes: ✗ FAILED (got %d)\n', len, length(rx));
            validation_pass = false;
        end
    catch ME
        fprintf('  %3d bytes: ✗ ERROR: %s\n', len, ME.message);
        validation_pass = false;
    end
end

% Check 2: Byte range (0-255)
fprintf('\n Byte range validation:\n');
try
    tx = uint8(randi([0, 255], 1, 100));
    rx = rf_emulator(tx);
    if all(rx >= 0) && all(rx <= 255) && isa(rx, 'uint8')
        fprintf('  All bytes in valid range [0-255]: ✓ OK\n');
    else
        fprintf('  Invalid byte values detected: ✗ FAILED\n');
        fprintf('  Min: %d, Max: %d, Type: %s\n', min(rx), max(rx), class(rx));
        validation_pass = false;
    end
catch ME
    fprintf('   ERROR: %s\n', ME.message);
    validation_pass = false;
end

% Check 3: Channel introduces errors
fprintf('\n✓ Channel error introduction:\n');
error_detected = false;
no_error_count = 0;
for i = 1:20
    try
        tx = uint8('TestMessage');
        [rx, ~] = rf_emulator(tx);
        if any(tx ~= rx)
            error_detected = true;
        else
            no_error_count = no_error_count + 1;
        end
    catch
        % Ignore errors for this test
    end
end

if error_detected
    fprintf('  Channel introduces errors: ✓ OK\n');
    fprintf('  (No errors in %d/20 trials - acceptable)\n', no_error_count);
else
    fprintf('  No errors detected in any trial: ⚠ WARNING\n');
    fprintf('  Channel may be too clean (SNR too high)\n');
end

% ============================================================
% Final Summary
% ============================================================
fprintf('\n╔════════════════════════════════════════════════╗\n');
fprintf('║              TEST SUMMARY                      ║\n');
fprintf('╚════════════════════════════════════════════════╝\n');

if validation_pass && success_count >= 95
    fprintf(' All validation tests PASSED\n');
    fprintf(' RF channel is working correctly\n');
    fprintf(' Average BER: %.4f (acceptable for SNR=%ddB)\n', mean(ber_samples), cfg.snr_db);
    fprintf(' Ready to run full simulation\n\n');
    fprintf('Next steps:\n');
    fprintf('  1. docker-compose up -d --build\n');
    fprintf('  2. python simurf_matlab_bridge.py\n');
    fprintf('  3. Watch receiver logs: docker logs -f simurf_receiver\n');
else
    fprintf(' Some validation tests FAILED\n');
    if success_count < 95
        fprintf('   Only %d/100 trials succeeded\n', success_count);
    end
    fprintf(' Please review RF emulator configuration\n');
end

fprintf('\n');