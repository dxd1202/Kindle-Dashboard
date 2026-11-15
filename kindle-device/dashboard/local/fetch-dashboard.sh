#!/bin/sh
output=$1
[ -n "$output" ] || exit 1
dir=$(dirname "$0")/..
url=${DASHBOARD_IMAGE_URL:-https://dxd1202.github.io/Kindle-Dashboard/output.png}
tmp=$(mktemp "${output}.XXXXXX") || exit 1
trap 'rm -f "$tmp"' EXIT
trap 'exit 1' HUP INT TERM

# Bound the download and keep the last image if the response is unusable.
"$dir/xh" --timeout 60 -d -q -o "$tmp" get "$url" || exit 1
size=$(wc -c < "$tmp") || exit 1
[ "$size" -gt 45 ] || exit 1
signature=$(od -An -tx1 -N8 "$tmp" | tr -d ' \n')
ending=$(tail -c 12 "$tmp" | od -An -tx1 | tr -d ' \n')
if [ "$signature" != 89504e470d0a1a0a ] || [ "$ending" != 0000000049454e44ae426082 ]; then
    echo "The response does not contain a complete PNG" >&2
    exit 1
fi
mv -f "$tmp" "$output"
