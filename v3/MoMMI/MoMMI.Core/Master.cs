using System;
using System.Reflection;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using Discord;
using Discord.WebSocket;
using MoMMI.Core.Logging;
using MoMMI.Core.Utility;
using Nito.AsyncEx;

namespace MoMMI.Core
{
    public interface IMaster
    {
        IConfigManager ConfigManager { get; }
        ILogManager LogManager { get; }
        IModuleManager ModuleManager { get; }

        DiscordSocketClient DiscordClient { get; }
    }

    internal sealed class Master : IMaster
    {
        public IConfigManagerInternal ConfigManager { get; }
        public ILogManager LogManager { get; }
        public IModuleManager ModuleManager { get; }

        IConfigManager IMaster.ConfigManager => ConfigManager;

        public DiscordSocketClient DiscordClient { get; private set; }

        private readonly ISawmill _discordSawmill;
        private readonly ISawmill _chatSawmill;
        private readonly ISawmill _masterSawmill;

        private readonly MSynchronizationContext _mainLoopSynchronizationContext;
        private readonly Channel<(SendOrPostCallback d, object state)> _mainLoopChannel;

        private readonly AsyncManualResetEvent _discordReadyEvent = new AsyncManualResetEvent(false);
        private readonly AsyncManualResetEvent _shutdownEvent = new AsyncManualResetEvent();

        private bool _shuttingDown;

        public Master(IConfigManagerInternal configManager, ILogManager logManager)
        {
            ModuleManager = new ModuleManager(this, logManager.GetSawmill("modules"));
            ConfigManager = configManager;
            LogManager = logManager;

            _discordSawmill = logManager.GetSawmill("discord");
            _chatSawmill = logManager.GetSawmill("chat");
            _masterSawmill = logManager.GetSawmill("master");

            DiscordClient = new DiscordSocketClient();

            DiscordClient.Log += message =>
            {
                _discordSawmill.Log(message.Severity.Convert(), "{0}: {1}", message.Source, message.Message);
                return Task.CompletedTask;
            };

            DiscordClient.MessageReceived += message =>
            {
                _chatSawmill.Info(message.Content);
                Spawn(() => OnMessageReceived(message));
                return Task.CompletedTask;
            };

            DiscordClient.Ready += () =>
            {
                Spawn(() => _discordReadyEvent.Set());
                return Task.CompletedTask;
            };

            _mainLoopChannel = Channel.CreateUnbounded<(SendOrPostCallback d, object state)>(new UnboundedChannelOptions
            {
                SingleReader = true
            });

            _mainLoopSynchronizationContext = new MSynchronizationContext(_mainLoopChannel.Writer);
        }

        public void Run()
        {
            AppDomain.CurrentDomain.ProcessExit += (sender, args) =>
            {
                Console.WriteLine("Shutting down!");
                Spawn(Shutdown);
                // Returning from this callback causes the process to hard exit,
                // so we wait here to shut down gracefully.
                _shutdownEvent.Wait();
            };

            Console.CancelKeyPress += (sender, args) =>
            {
                args.Cancel = true;
                _masterSawmill.Info("Received CancelKeyPress, shutting down!");
                Spawn(Shutdown);
            };

            SynchronizationContext.SetSynchronizationContext(_mainLoopSynchronizationContext);
            Spawn(async () =>
            {
                async Task ConnectDiscord()
                {
                    await DiscordClient.LoginAsync(TokenType.Bot, ConfigManager.MainConfig.DiscordToken);
                    await DiscordClient.StartAsync();
                    await _discordReadyEvent.WaitAsync();
                }

                var discordTask = ConnectDiscord();

                // Load modules while we wait on Discord.
                ModuleManager.ReloadModules();

                await discordTask;

                // Waiting on Discord done.
                _masterSawmill.Debug("Guilds:");
                foreach (var guild in DiscordClient.Guilds)
                {
                    _masterSawmill.Debug("  {0}", guild.Name);
                }
            });
            MainLoop();
        }

        private async void OnMessageReceived(SocketMessage message)
        {
            if (_shuttingDown)
            {
                return;
            }

            foreach (var module in ModuleManager.Modules)
            {
                var type = module.GetType();
                foreach (var method in type.GetMethods())
                {
                    var attribute = method.GetCustomAttribute<CommandAttribute>();
                    if (attribute == null)
                    {
                        continue;
                    }

                    var match = attribute.CompiledRegex.Match(message.Content);
                    if (match.Success)
                    {
                        var task = (Task) method.Invoke(module, new object[] {message.Channel});
                        await task;
                    }
                }
            }
        }

        public void Shutdown()
        {
            _masterSawmill.Info("Shutting down!");

            Spawn(async () =>
            {
                _shuttingDown = true;
                // Actual shutdown code goes here.

                // Cleanly shut down the Discord connection.
                await DiscordClient.LogoutAsync();
                await DiscordClient.StopAsync();
                DiscordClient.Dispose();

                // Shutdown done, mark us as shut down
                _shutdownEvent.Set();
            });
        }

        private void Spawn(Action p)
        {
            _mainLoopSynchronizationContext.Post(d => p(), null);
        }

        // This is ran inside the MoMMI main loop thread.
        // We pump a synchronization context in a single thread.
        // This ensures all the actually complicated logic of MoMMI is single threaded.
        // Making it less of a hassle to have to deal with synchronization.
        // Also gives US control of synchronization more,
        // because really Discord.Net's default method is kinda bad IMO.
        private void MainLoop()
        {
            while (!_shutdownEvent.IsSet)
            {
                var (d, state) = _mainLoopChannel.Reader.ReadAsync().AsTask().Result;
                d(state);
            }
        }

        private sealed class MSynchronizationContext : SynchronizationContext
        {
            private readonly ChannelWriter<(SendOrPostCallback d, object state)> _channel;

            public MSynchronizationContext(ChannelWriter<(SendOrPostCallback d, object state)> channel)
            {
                _channel = channel;
            }

            public override void Post(SendOrPostCallback d, object state)
            {
                _channel.TryWrite((d, state));
            }
        }
    }
}
