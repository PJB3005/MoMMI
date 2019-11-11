using MoMMI.Core.Utility;
using YamlDotNet.RepresentationModel;

namespace MoMMI.Core.Config
{
    internal sealed class MainConfig : IFromYaml
    {
        public string DiscordToken { get; private set; }

        public void LoadFrom(YamlNode node)
        {
            if (!(node is YamlMappingNode mapping))
            {
                throw new ConfigException("Expected a mapping at the root of the main config.");
            }

            mapping.TryReadScalar<string>("bot token", s => DiscordToken = s, () => throw new ConfigException());
        }
    }
}
