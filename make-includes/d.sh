
#!/bin/bash
set -e
if grep -qE "(Microsoft|WSL)" /proc/version &> /dev/null ; then
    echo "Windows 10 Bash"
else
    echo "Anything else"
fi
