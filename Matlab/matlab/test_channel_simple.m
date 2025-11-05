% Simple test for channel simulator
clear; clc;

disp('=== SimuRF MATLAB Channel Test ===');

% Create test packet (100 bytes)
test_packet = uint8(randi([0 255], 100, 1));
disp(['Test packet size: ' num2str(length(test_packet)) ' bytes']);

% Setup channel parameters
params.carrier_freq = 2.4e9;
params.sample_rate = 20e6;
params.snr = 15;
params.delay_spread = 50e-9;
params.doppler = 10;

disp(' ');
disp('Channel Parameters:');
disp(['  SNR: ' num2str(params.snr) ' dB']);
disp(['  Delay Spread: ' num2str(params.delay_spread*1e9) ' ns']);
disp(['  Doppler: ' num2str(params.doppler) ' Hz']);

% Run simulation
disp(' ');
disp('Running channel simulation...');
tic;
output_packet = matlab_channel_sim(test_packet, params);
elapsed = toc;

% Calculate results
bit_errors = sum(test_packet ~= output_packet);
byte_error_rate = bit_errors / length(test_packet);

disp(' ');
disp('=== Results ===');
disp(['Processing time: ' num2str(elapsed*1000) ' ms']);
disp(['Byte errors: ' num2str(bit_errors) '/' num2str(length(test_packet))]);
disp(['Byte error rate: ' num2str(byte_error_rate*100) '%']);

% Verify output
if length(output_packet) == length(test_packet)
    disp('✓ Output size matches input');
else
    disp('✗ Output size mismatch!');
end

if bit_errors > 0 && bit_errors < length(test_packet)
    disp('✓ Channel simulation working (some errors introduced)');
else
    disp('⚠ Warning: Check channel simulation');
end

disp(' ');
disp('Test complete!');