using System;
using System.Globalization;
using YamlDotNet.RepresentationModel;

namespace MoMMI.Core.Utility
{
    public static class YamlExt
    {
        public static void TryReadScalar<T>(this YamlMappingNode mapping, string nodeName, Action<T> onExist,
            Action onError)
        {
            if (!mapping.Children.TryGetValue(nodeName, out var node))
            {
                return;
            }

            if (!(node is YamlScalarNode scalar))
            {
                onError();
                return;
            }

            // Parse value
            if (typeof(T) == typeof(string))
            {
                onExist((T)(object)scalar.Value);
                return;
            }

            if (typeof(T) == typeof(int))
            {
                onExist((T)(object)int.Parse(scalar.Value, CultureInfo.InvariantCulture));
                return;
            }

            if (typeof(T) == typeof(float))
            {
                onExist((T)(object)float.Parse(scalar.Value, CultureInfo.InvariantCulture));
                return;
            }

            throw new NotImplementedException();
        }
    }
}
