function save_complex_samples(complex_samples, filename)
% SAVE_COMPLEX_SAMPLES - Save complex samples to binary file
%   Format: interleaved real and imaginary parts as float32

    % Convert to interleaved real/imaginary
    interleaved = zeros(1, 2 * length(complex_samples));
    interleaved(1:2:end) = real(complex_samples);
    interleaved(2:2:end) = imag(complex_samples);
    
    % Save as binary
    fid = fopen(filename, 'wb');
    fwrite(fid, interleaved, 'float32');
    fclose(fid);
    
    fprintf('Saved %d samples to %s\n', length(complex_samples), filename);
end