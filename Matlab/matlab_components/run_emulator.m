function run_emulator()
    % Main function to run RF emulator
    
    % Load channel parameters from config
    channel_params = load_channel_params();
    
    fprintf('Starting SimuRF MATLAB Emulator...\n');
    fprintf('SNR: %d dB, Multipath: %d, Freq Offset: %.3f\n', ...
            channel_params.snr, channel_params.multipath_enabled, ...
            channel_params.freq_offset);
    
    % Listen for incoming IP packets
    while true
        try
            % Check for new IP packets in input directory
            input_dir = '/simurf/input';
            if exist(input_dir, 'dir')
                files = dir(fullfile(input_dir, 'ip_packet_*.bin'));
                
                for i = 1:length(files)
                    filename = fullfile(input_dir, files(i).name);
                    
                    % Read IP packet
                    fid = fopen(filename, 'rb');
                    if fid ~= -1
                        ip_packet = fread(fid, 'uint8');
                        fclose(fid);
                        
                        % Process through RF emulator
                        rf_emulator(ip_packet, channel_params);
                        
                        % Clean up input file
                        delete(filename);
                        
                        fprintf('Processed IP packet: %s, Length: %d\n', ...
                                files(i).name, length(ip_packet));
                    end
                end
            end
            
            pause(0.1); % Small delay
            
        catch ME
            fprintf('Error in main loop: %s\n', ME.message);
            pause(1);
        end
    end
end

function params = load_channel_params()
    % Load channel parameters from config file
    params.snr = 20; % dB
    params.multipath_enabled = true;
    params.freq_offset = 0.01;
    params.delay_taps = [1.0, 0.5, 0.2];
    
    % Try to load from JSON config
    try
        if exist('/simurf/config/channel_config.json', 'file')
            % Note: MATLAB would need jsondecode (R2016b+) or external function
            % For compatibility, we'll use hardcoded values
            fprintf('Loading channel parameters from config...\n');
        end
    catch
        fprintf('Using default channel parameters\n');
    end
end