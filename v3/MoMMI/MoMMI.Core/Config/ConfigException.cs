using System;
using System.Runtime.Serialization;

namespace MoMMI.Core.Config
{
    [Serializable]
    public class ConfigException : Exception
    {
        public ConfigException()
        {
        }

        public ConfigException(string message) : base(message)
        {
        }

        public ConfigException(string message, Exception inner) : base(message, inner)
        {
        }

        protected ConfigException(
            SerializationInfo info,
            StreamingContext context) : base(info, context)
        {
        }
    }
}
