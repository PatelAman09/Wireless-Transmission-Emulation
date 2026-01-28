function init_channel(cfg)
    persistent channelState
    channelState = cfg;

    assignin('base', 'CHANNEL_CFG', cfg);
end
