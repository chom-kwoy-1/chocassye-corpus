for  file  in  **/*.utf8; do
     mv   "$file"  "${file%.utf8}.txt"
done
