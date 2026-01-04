% Debug script to check what rf_emulator is actually returning

clear; clc;

fprintf('=== RF Emulator Output Diagnostics ===\n\n');

% Load config
config_path = '../config/matlab_channel_config.json';
cfg = jsondecode(fileread(config_path));
init_channel(cfg);

% Test with simple input
msg = 'Hello';
tx = uint8(msg);

fprintf('Input:\n');
fprintf('  Message: "%s"\n', msg);
fprintf('  Bytes: [%s]\n', num2str(tx));
fprintf('  Type: %s\n', class(tx));
fprintf('  Size: %s\n', mat2str(size(tx)));
fprintf('  Values: ');
for i = 1:length(tx)
    fprintf('%d ', tx(i));
end
fprintf('\n\n');

% Call RF emulator
fprintf('Calling rf_emulator...\n');
[rx, metrics] = rf_emulator(tx);

fprintf('\nOutput:\n');
fprintf('  Type: %s\n', class(rx));
fprintf('  Size: %s\n', mat2str(size(rx)));
fprintf('  Length: %d\n', length(rx));

% Check if it's actually uint8
if ~isa(rx, 'uint8')
    fprintf('  ⚠ WARNING: Output is not uint8! Converting...\n');
    rx = uint8(rx);
end

% Check values
fprintf('  Min value: %d\n', min(rx));
fprintf('  Max value: %d\n', max(rx));

if any(rx > 255) || any(rx < 0)
    fprintf('   ERROR: Values outside uint8 range!\n');
else
    fprintf('   All values in valid range\n');
end

fprintf('  Values: ');
for i = 1:length(rx)
    fprintf('%d ', rx(i));
end
fprintf('\n');

fprintf('  As string: "%s"\n', char(rx));

fprintf('\nMetrics:\n');
fprintf('  BER: %.4f\n', metrics.ber);
fprintf('  Bit errors: %d/%d\n', metrics.bit_errors, length(tx)*8);
fprintf('  Byte errors: %d/%d\n', metrics.byte_errors, metrics.bytes_total);

fprintf('\n=== Diagnosis Complete ===\n');

% Additional check: compare element by element
fprintf('\nByte-by-byte comparison:\n');
fprintf('  Idx | TX  | RX  | Match\n');
fprintf('  ----+-----+-----+------\n');
for i = 1:min(length(tx), length(rx))
    match = tx(i) == rx(i);
    marker = ' ';
    if ~match
        marker = '✗';
    end
    fprintf('  %3d | %3d | %3d | %s\n', i, tx(i), rx(i), marker);
end

if length(tx) ~= length(rx)
    fprintf('\n   Length mismatch: TX=%d, RX=%d\n', length(tx), length(rx));
else
    fprintf('\n   Lengths match\n');
end