function [complex_samples, channel_info] = professional_rf_emulator(ip_packet_bytes, config_file)
% PROFESSIONAL_RF_EMULATOR - Advanced wireless transmission simulation
%   Enhanced version with multipath, interference, and advanced metrics

    fprintf('=== MATLAB Professional RF Emulator v2.0 ===\n');
    
    % Load configuration
    if nargin < 2
        config_file = '/simurf/config/matlab_channel_config.json';
    end
    config = load_config(config_file);
    
    fprintf('Configuration: %s, SNR: %d dB, Modulation: %s\n', ...
            config.channel_model, config.snr_db, config.modulation_scheme);
    
    % Convert IP packet to binary stream
    binary_data = ip_to_binary(ip_packet_bytes);
    fprintf('Input: %d bytes -> %d bits\n', length(ip_packet_bytes), length(binary_data));
    
    % Add error correction coding (optional)
    if isfield(config, 'use_fec') && config.use_fec
        encoded_data = apply_fec_encoding(binary_data, config);
        fprintf('FEC: %d bits -> %d coded bits (Rate %.2f)\n', ...
                length(binary_data), length(encoded_data), ...
                length(binary_data)/length(encoded_data));
        binary_data = encoded_data;
    end
    
    % Advanced modulation
    modulated_signal = advanced_modulation(binary_data, config);
    
    % Apply pulse shaping
    if isfield(config, 'use_pulse_shaping') && config.use_pulse_shaping
        shaped_signal = apply_pulse_shaping(modulated_signal, config);
    else
        shaped_signal = modulated_signal;
    end
    
    % Professional channel simulation with multipath
    [received_signal, channel_info] = professional_channel_simulation(shaped_signal, config);
    
    % Add interference if configured
    if isfield(config, 'interference_power_db') && config.interference_power_db > -Inf
        received_signal = add_interference(received_signal, config);
        channel_info.interference_power_db = config.interference_power_db;
    end
    
    % Generate complex samples
    complex_samples = received_signal;
    
    % Additional metrics
    channel_info.papr = calculate_papr(complex_samples);
    channel_info.spectral_efficiency = calculate_spectral_efficiency(config);
    
    fprintf('Processing complete: %d complex samples generated\n', length(complex_samples));
    fprintf('PAPR: %.2f dB, Spectral Efficiency: %.2f bits/s/Hz\n', ...
            channel_info.papr, channel_info.spectral_efficiency);
end

function config = load_config(config_file)
    try
        config_json = fileread(config_file);
        config_data = jsondecode(config_json);
        
        config.snr_db = config_data.snr_db;
        config.channel_model = config_data.channel_model;
        config.modulation_scheme = config_data.modulation_scheme;
        config.carrier_frequency = config_data.carrier_frequency;
        config.sample_rate = config_data.sample_rate;
        config.doppler_shift = config_data.doppler_shift;
        
        % Optional parameters
        if isfield(config_data, 'use_fec')
            config.use_fec = config_data.use_fec;
        end
        if isfield(config_data, 'use_pulse_shaping')
            config.use_pulse_shaping = config_data.use_pulse_shaping;
        end
        if isfield(config_data, 'multipath_delays')
            config.multipath_delays = config_data.multipath_delays;
        end
        if isfield(config_data, 'multipath_gains')
            config.multipath_gains = config_data.multipath_gains;
        end
        if isfield(config_data, 'interference_power_db')
            config.interference_power_db = config_data.interference_power_db;
        end
        
    catch
        fprintf('Using default configuration\n');
        config.snr_db = 20;
        config.channel_model = 'Rayleigh';
        config.modulation_scheme = 'QPSK';
        config.carrier_frequency = 2.4e9;
        config.sample_rate = 10e6;
        config.doppler_shift = 100;
    end
end

function binary_data = ip_to_binary(ip_packet_bytes)
    binary_data = [];
    for i = 1:length(ip_packet_bytes)
        byte_bits = dec2bin(ip_packet_bytes(i), 8) - '0';
        binary_data = [binary_data, byte_bits];
    end
    binary_data = binary_data(:)';
end

function encoded_data = apply_fec_encoding(binary_data, config)
% Simple repetition code or convolutional encoding
    % Repetition code (rate 1/3)
    encoded_data = repmat(binary_data, 1, 3);
end

function shaped_signal = apply_pulse_shaping(symbols, config)
% Root Raised Cosine pulse shaping
    span = 10;  % Filter span in symbols
    sps = 4;    % Samples per symbol
    beta = 0.5; % Roll-off factor
    
    rrc_filter = rcosdesign(beta, span, sps, 'sqrt');
    
    % Upsample and filter
    upsampled = upsample(symbols, sps);
    shaped_signal = filter(rrc_filter, 1, upsampled);
    
    % Normalize
    shaped_signal = shaped_signal / max(abs(shaped_signal));
end

function modulated_signal = advanced_modulation(binary_data, config)
    fprintf('Modulation: %s\n', config.modulation_scheme);
    
    switch config.modulation_scheme
        case 'BPSK'
            symbols = 2 * binary_data - 1;
            modulated_signal = symbols;
            
        case 'QPSK'
            if mod(length(binary_data), 2) ~= 0
                binary_data = [binary_data, 0];
            end
            reshaped_data = reshape(binary_data, 2, []);
            symbols = zeros(1, size(reshaped_data, 2));
            for i = 1:size(reshaped_data, 2)
                bits = reshaped_data(:, i)';
                if isequal(bits, [0, 0])
                    symbols(i) = (1 + 1j) / sqrt(2);
                elseif isequal(bits, [0, 1])
                    symbols(i) = (-1 + 1j) / sqrt(2);
                elseif isequal(bits, [1, 1])
                    symbols(i) = (-1 - 1j) / sqrt(2);
                elseif isequal(bits, [1, 0])
                    symbols(i) = (1 - 1j) / sqrt(2);
                end
            end
            modulated_signal = symbols;
            
        case '16QAM'
            if mod(length(binary_data), 4) ~= 0
                binary_data = [binary_data, zeros(1, 4 - mod(length(binary_data), 4))];
            end
            reshaped_data = reshape(binary_data, 4, []);
            symbols = zeros(1, size(reshaped_data, 2));
            for i = 1:size(reshaped_data, 2)
                bits = reshaped_data(:, i)';
                symbols(i) = qam16_mapper(bits);
            end
            modulated_signal = symbols;
            
        case '64QAM'
            if mod(length(binary_data), 6) ~= 0
                binary_data = [binary_data, zeros(1, 6 - mod(length(binary_data), 6))];
            end
            reshaped_data = reshape(binary_data, 6, []);
            symbols = zeros(1, size(reshaped_data, 2));
            for i = 1:size(reshaped_data, 2)
                bits = reshaped_data(:, i)';
                symbols(i) = qam64_mapper(bits);
            end
            modulated_signal = symbols;
            
        otherwise
            error('Unsupported modulation scheme: %s', config.modulation_scheme);
    end
    
    fprintf('   Generated %d symbols\n', length(modulated_signal));
end

function symbol = qam16_mapper(bits)
    constellation = [-3-3j, -3-1j, -3+3j, -3+1j, ...
                     -1-3j, -1-1j, -1+3j, -1+1j, ...
                      3-3j,  3-1j,  3+3j,  3+1j, ...
                      1-3j,  1-1j,  1+3j,  1+1j] / sqrt(10);
    index = bin2dec(num2str(bits));
    symbol = constellation(index + 1);
end

function symbol = qam64_mapper(bits)
    % 64-QAM constellation
    symbols_i = [-7, -5, -3, -1, 1, 3, 5, 7];
    symbols_q = [-7, -5, -3, -1, 1, 3, 5, 7];
    
    i_bits = bits(1:3);
    q_bits = bits(4:6);
    
    i_idx = bin2dec(num2str(i_bits)) + 1;
    q_idx = bin2dec(num2str(q_bits)) + 1;
    
    symbol = (symbols_i(i_idx) + 1j * symbols_q(q_idx)) / sqrt(42);
end

function [received_signal, channel_info] = professional_channel_simulation(tx_signal, config)
    fprintf('Channel: %s model\n', config.channel_model);
    
    channel_info.snr_db = config.snr_db;
    channel_info.channel_model = config.channel_model;
    
    % Multipath channel if configured
    if isfield(config, 'multipath_delays') && ~isempty(config.multipath_delays)
        tx_signal = apply_multipath(tx_signal, config);
        channel_info.multipath_enabled = true;
    end
    
    % Apply channel model
    switch config.channel_model
        case 'AWGN'
            snr_linear = 10^(config.snr_db / 10);
            signal_power = mean(abs(tx_signal).^2);
            noise_power = signal_power / snr_linear;
            
            noise = sqrt(noise_power/2) * (randn(size(tx_signal)) + 1j*randn(size(tx_signal)));
            channel_output = tx_signal + noise;
            
        case 'Rayleigh'
            snr_linear = 10^(config.snr_db / 10);
            signal_power = mean(abs(tx_signal).^2);
            noise_power = signal_power / snr_linear;
            
            % Rayleigh fading
            h = (randn(size(tx_signal)) + 1j*randn(size(tx_signal))) / sqrt(2);
            faded_signal = tx_signal .* h;
            
            noise = sqrt(noise_power/2) * (randn(size(tx_signal)) + 1j*randn(size(tx_signal)));
            channel_output = faded_signal + noise;
            
            channel_info.fading_coefficients = h;
            channel_info.avg_fade_depth = 10*log10(mean(abs(h).^2));
            
        case 'Rician'
            K = 3;
            snr_linear = 10^(config.snr_db / 10);
            
            mean_path = sqrt(K/(K+1));
            random_path = sqrt(1/(2*(K+1))) * (randn(size(tx_signal)) + 1j*randn(size(tx_signal)));
            h = mean_path + random_path;
            
            faded_signal = tx_signal .* h;
            
            noise_power = mean(abs(faded_signal).^2) / snr_linear;
            noise = sqrt(noise_power/2) * (randn(size(tx_signal)) + 1j*randn(size(tx_signal)));
            channel_output = faded_signal + noise;
            
            channel_info.fading_coefficients = h;
            channel_info.rician_k_factor = K;
            
        otherwise
            error('Unsupported channel model: %s', config.channel_model);
    end
    
    % Apply frequency offset (Doppler)
    if config.doppler_shift > 0
        t = (0:length(tx_signal)-1) / config.sample_rate;
        freq_shift = exp(1j * 2 * pi * config.doppler_shift * t);
        channel_output = channel_output .* freq_shift;
        channel_info.frequency_offset = config.doppler_shift;
    end
    
    received_signal = channel_output;
    
    % Calculate performance metrics
    channel_info.evm = calculate_evm(tx_signal, received_signal);
    channel_info.ber = calculate_ber(tx_signal, received_signal, config.modulation_scheme);
    channel_info.snr_measured = calculate_snr(received_signal, tx_signal);
    
    fprintf('   EVM: %.2f%%, BER: %.2e, Measured SNR: %.2f dB\n', ...
            channel_info.evm*100, channel_info.ber, channel_info.snr_measured);
end

function signal_with_multipath = apply_multipath(signal, config)
% Add multipath components
    delays = config.multipath_delays;  % in samples
    gains = config.multipath_gains;    % linear gains
    
    signal_with_multipath = zeros(size(signal));
    
    for i = 1:length(delays)
        delay = delays(i);
        gain = gains(i);
        
        if delay == 0
            signal_with_multipath = signal_with_multipath + gain * signal;
        else
            delayed = [zeros(1, delay), signal(1:end-delay)];
            signal_with_multipath = signal_with_multipath + gain * delayed;
        end
    end
end

function signal_with_interference = add_interference(signal, config)
% Add interference signal
    interference_power_db = config.interference_power_db;
    signal_power = mean(abs(signal).^2);
    
    interference_power_linear = 10^(interference_power_db / 10) * signal_power;
    
    % Random interference
    interference = sqrt(interference_power_linear/2) * ...
                   (randn(size(signal)) + 1j*randn(size(signal)));
    
    signal_with_interference = signal + interference;
end

function papr = calculate_papr(signal)
% Peak-to-Average Power Ratio
    peak_power = max(abs(signal).^2);
    avg_power = mean(abs(signal).^2);
    papr = 10 * log10(peak_power / avg_power);
end

function spec_eff = calculate_spectral_efficiency(config)
% Calculate spectral efficiency in bits/s/Hz
    switch config.modulation_scheme
        case 'BPSK'
            bits_per_symbol = 1;
        case 'QPSK'
            bits_per_symbol = 2;
        case '16QAM'
            bits_per_symbol = 4;
        case '64QAM'
            bits_per_symbol = 6;
        otherwise
            bits_per_symbol = 2;
    end
    spec_eff = bits_per_symbol;
end

function evm = calculate_evm(tx_signal, rx_signal)
    error_vector = rx_signal - tx_signal;
    evm = sqrt(mean(abs(error_vector).^2) / mean(abs(tx_signal).^2));
end

function snr_db = calculate_snr(rx_signal, tx_signal)
% Measured SNR
    signal_power = mean(abs(tx_signal).^2);
    noise_power = mean(abs(rx_signal - tx_signal).^2);
    snr_db = 10 * log10(signal_power / noise_power);
end

function ber = calculate_ber(tx_signal, rx_signal, modulation)
    switch modulation
        case 'BPSK'
            tx_bits = real(tx_signal) > 0;
            rx_bits = real(rx_signal) > 0;
            errors = sum(tx_bits ~= rx_bits);
            ber = errors / length(tx_bits);
            
        case 'QPSK'
            tx_symbols = [real(tx_signal) > 0; imag(tx_signal) > 0];
            rx_symbols = [real(rx_signal) > 0; imag(rx_signal) > 0];
            errors = sum(tx_symbols(:) ~= rx_symbols(:));
            ber = errors / (2 * length(tx_signal));
            
        otherwise
            ber = 1e-4;
    end
end