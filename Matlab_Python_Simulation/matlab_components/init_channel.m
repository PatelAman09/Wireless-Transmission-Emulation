function init_channel(cfg)
%INIT_CHANNEL Store channel configuration globally
%   cfg is a struct passed from Python

    assignin('base', 'CHANNEL_CFG', cfg);
end
