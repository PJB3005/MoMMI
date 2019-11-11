using System.IO;
using MoMMI.Core.Config;
using MoMMI.Core.Logging;
using YamlDotNet.RepresentationModel;
using YamlDotNet.Serialization;

namespace MoMMI.Core
{
    internal sealed class ConfigManager : IConfigManagerInternal
    {
        public const string Main = "main.yml";
        public const string Servers = "servers.yml";
        public const string Modules = "modules.yml";

        private readonly string _configPath;
        private readonly ISawmill _sawmill;

        public MainConfig MainConfig { get; private set; }

        public ConfigManager(ISawmill sawmill, string configPath)
        {
            _sawmill = sawmill;
            _configPath = configPath;
        }

        public void LoadConfig()
        {
            var mainPath = Path.Combine(_configPath, Main);

            _sawmill.Debug("Loading main config from {0}!", mainPath);

            var stream = new YamlStream();
            using (var reader = File.OpenText(mainPath))
            {
                stream.Load(reader);
            }

            var node = stream.Documents[0].RootNode;
            MainConfig = new MainConfig();
            MainConfig.LoadFrom(node);
        }
    }

    internal interface IConfigManagerInternal : IConfigManager
    {
        MainConfig MainConfig { get; }
    }

    public interface IConfigManager
    {
    }
}
