using System;
using System.Text.RegularExpressions;
using JetBrains.Annotations;

namespace MoMMI.Core
{
    [AttributeUsage(AttributeTargets.Method)]
    public sealed class CommandAttribute : Attribute
    {
        public string Regex { get; }
        public Regex CompiledRegex { get; }

        public CommandAttribute([RegexPattern] string regex, RegexOptions regexOptions = RegexOptions.None)
        {
            Regex = regex;
            CompiledRegex = new Regex(Regex, regexOptions);
        }
    }
}
