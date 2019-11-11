using YamlDotNet.RepresentationModel;

namespace MoMMI.Core.Config
{
    public interface IFromYaml
    {
        void LoadFrom(YamlNode node);
    }
}
