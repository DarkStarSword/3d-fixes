#!/bin/sh -e

MIGOTO_DIR=~/3DMigoto-cleaned
GITSTATS=~/gitstats/gitstats
STATS_DIR=~/var/www/ian.ozlabs.org/htdocs/3Dmigoto-stats

cd "${MIGOTO_DIR}"
git fetch -p

if [ "$(git show -s --pretty=format:%H origin/master)" = "$(git show -s --pretty=format:%H last)" ]; then
	echo No updates to master, aborting
	exit
fi

git reset --hard origin/master

PARENT_FILTER=true
ENV_FILTER=true
INDEX_FILTER=true

# Re-attribute master source commit to Chiri:
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_COMMIT" = 1ba6f7e8c8bf6bca3ef49406e7e48698c8d7f4dd ]; then export GIT_AUTHOR_NAME=Chiri; export GIT_AUTHOR_EMAIL=; fi'

# Give Bo3b a consistent author name & email (we can maybe use .mailmap for this):
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_AUTHOR_EMAIL" = 3dmigoto@bo3b.net -o "$GIT_AUTHOR_EMAIL" = github@bo3b.net -o "$GIT_AUTHOR_EMAIL" = bitbucket@bo3b.net -o "$GIT_AUTHOR_EMAIL" = git@bo3b.net -o "$GIT_AUTHOR_EMAIL" = 3Dmigoto@bo3b.net ]; then export GIT_AUTHOR_NAME=Bo3b; export GIT_AUTHOR_EMAIL=github@bo3b.net; fi'
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_AUTHOR_NAME" = bo3b ]; then export GIT_AUTHOR_NAME=Bo3b; export GIT_AUTHOR_EMAIL=github@bo3b.net; fi'

# Give Flugan a consistent author name:
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_AUTHOR_NAME" = "Ulf Jälmbrant" ]; then export GIT_AUTHOR_NAME=Flugan; fi'

# Give llyzs a consistent author name & email:
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_AUTHOR_EMAIL" = llyzs.vic@gmail.com ]; then export GIT_AUTHOR_NAME=llyzs; export GIT_AUTHOR_EMAIL=llyzs.ki@gmail.com; fi'

# Rename me to DarkStarSword:
ENV_FILTER="$ENV_FILTER;"'if [ "$GIT_AUTHOR_EMAIL" = darkstarsword@gmail.com ]; then export GIT_AUTHOR_NAME="DarkStarSword"; fi'

# Remove game fixes:
INDEX_FILTER="$INDEX_FILTER;"'git rm -fr --cached --ignore-unmatch FC4 Witcher3 Batman AC3 AC4 ACLiberation Alien Arma3 BF4 Crysis2 DragonAge Ghosts GTA5 JC3 LOTF Mordor SR3 SR4 WatchDogs ACUnity BattleBorn Battlefront BFH BO3 Cars CoH2 Crysis3 Division DR3 EscapeDI Golf KF2 MadMax MirrorsEdge Outlast2 QB RE7 RoTR TheCrew DirectX9/AC4 BinaryDecompiler/AC4 D3DCompiler_39/AC4 D3DCompiler_41/AC4 D3DCompiler_42/AC4 D3DCompiler_43/AC4 D3DCompiler_46/AC4 DirectX10/AC4 DirectX11/AC4 DirectXGI/AC4 NVAPI/AC4 "Far Cry 4" >/dev/null'

# Remove some third party code (breaks the build, but we are interested in collecting stats for our work, not third parties):
INDEX_FILTER="$INDEX_FILTER;"'git rm -fr --cached --ignore-unmatch pcre2-10.30 DirectXTK crc32c-hw-1.0.5 nvapi.h >/dev/null'

# Not sure about this one:
#  Remove BinaryDecompiler, since that will be over-inflating Chiri's original commit by a good 5,500 LOC
#  OTOH we've actually modified it quite a bit in our repo that I would like to count, so... not sure
INDEX_FILTER="$INDEX_FILTER;"'git rm -fr --cached --ignore-unmatch BinaryDecompiler >/dev/null'

# Remove .lib, .pdb and .exe files - they are third party build products, not our code:
INDEX_FILTER="$INDEX_FILTER;"'git rm -fr --cached --ignore-unmatch *.lib *.pdb *.exe >/dev/null'

# TestShaders/GameExamples could be argued as being third party, or Bo3b (testing), but will be miasattributed to me, so just remove it:
INDEX_FILTER="$INDEX_FILTER;"'git rm -fr --cached --ignore-unmatch TestShaders/GameExamples >/dev/null'

# Remove squashed git subtree commits for DirectXTK:
PARENT_FILTER="$PARENT_FILTER;"'sed "s/-p 23206c54c87bd475a45a187fd4667e978b076b38//"'
PARENT_FILTER="$PARENT_FILTER;"'sed "s/-p 99ccacc35b11c850c9264bb19f8128b06d019a1f//"'

#echo
#echo Parent filter: "$PARENT_FILTER"
#echo
#echo Environment filter: "$ENV_FILTER"
#echo
#echo Index filter: "$INDEX_FILTER"
#echo

# Do the parent filter first, as the environment filter could change the SHA1s
# it is matching, and I'd rather refer to them by the SHA in master:
nice ionice -c 3 git filter-branch --parent-filter "$PARENT_FILTER" --prune-empty -f HEAD
nice ionice -c 3 git filter-branch --env-filter "$ENV_FILTER" --index-filter "$INDEX_FILTER" --prune-empty -f HEAD

nice ionice -c 3 "$GITSTATS" "$MIGOTO_DIR" "$STATS_DIR"

git branch -f last origin/master

# Cleanup references to keep the repository size small:
git reflog expire --all --expire-unreachable=now
git gc --prune=now

# Cool visualisations, but would be better if the size of the nodes reflected
# the file size:
# gource -f  --file-filter '^((?!\.(cpp|h)).)*$' --highlight-users -s 0.25
# gource -f  --highlight-users -s 0.25
