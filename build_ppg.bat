if not exist planpro-generator\ (
    git clone https://github.com/ctiedt/planpro-generator
)
cd planpro-generator
git pull
call ant

copy ppg.jar ..\