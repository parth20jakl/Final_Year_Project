# Setup guide: Android Studio, test phone, first Colab run

## A. Android Studio and SDK (this PC)

PC: i7-1355U, 8 GB RAM, about 35 GB free. 8 GB is the official minimum for Android Studio **without** the emulator,
so skip the emulator and test on the phone.

1. Download Android Studio for Windows from https://developer.android.com/studio .
2. Run the installer. Untick **Android Virtual Device** if offered. Keep the default folder.
3. First start: choose **Standard** setup, accept the licences, let it download the SDK.
4. Open **More Actions > SDK Manager** (or Settings > Languages & Frameworks > Android SDK).
   - *SDK Platforms*: tick **Android 16 (API 36)**.
   - *SDK Tools*: tick **Android SDK Build-Tools**, **Android SDK Platform-Tools**, **Android SDK Command-line Tools**.
   - NDK and CMake are not needed.
5. Add adb to PATH: Start > "Edit environment variables for your account" > `Path` > New >
   `%LOCALAPPDATA%\Android\Sdk\platform-tools` > OK. Close and reopen the terminal.
6. Check: `adb version` prints a version number.
7. Close heavy programs (Photoshop, many browser tabs) while building.

## B. Test phone: Samsung Galaxy S26 Ultra

1. Install the Samsung USB driver for Windows: https://developer.samsung.com/android-usb-driver . Restart the PC.
2. Phone: **Settings > About phone > Software information**, tap **Build number** 7 times, enter the PIN.
3. **Settings > Security and privacy > Auto Blocker**: turn it off (it blocks USB commands). It may turn itself on
   again; switch it back on yourself when you finish testing.
4. **Settings > Developer options**: turn on **USB debugging**.
5. Connect with a USB **data** cable. On the phone, tap **Allow** on the USB-debugging prompt and tick
   "Always allow from this computer".
6. Check: `adb devices` lists the phone with the word `device` (not `unauthorized`).
7. Collect the specifications (PowerShell) and send the output:
```
adb shell getprop ro.product.model
adb shell getprop ro.soc.manufacturer
adb shell getprop ro.soc.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.oneui
adb shell getprop ro.product.cpu.abilist
adb shell grep MemTotal /proc/meminfo
adb shell df -h /data
adb shell wm size
```
| Specification | Why it is needed |
|---|---|
| Model number (SM-S948...) | identifies the exact variant in the report |
| Chipset | speed results depend on it |
| RAM, free storage | model loading, saved logs |
| Android version, API level, One UI | app's target SDK and camera behaviour |
| CPU ABI (expected `arm64-v8a`) | which ONNX Runtime library is packaged |
| Screen resolution | preview and box scaling |

Benchmark conditions to keep fixed: same battery level range, not charging, power saving off, screen brightness
fixed, phone cool before each run.

**Report note:** this is a flagship phone, so frame rates will be higher than on a typical gate device. If a
mid-range phone can be borrowed, benchmark on both; otherwise state the limitation.

## C. First Colab run

Before starting: the repository on GitHub contains the latest notebook and scripts (push them first), and
`dataset_v5.zip` exists in `dataset/frozen/`.

1. **Drive:** upload `dataset/frozen/dataset_v5.zip` into the dataset folder named in the notebook (`FOLDER_ID`).
   Share that folder only with named accounts.
2. **GitHub token** (the repository is private). The repository owner opens GitHub > Settings > Developer settings >
   Personal access tokens > Fine-grained tokens > Generate:
   repository access = only `Final_Year_Project`; permission **Contents: Read-only**; short expiry.
3. Open https://colab.research.google.com , **File > Upload notebook**, choose `colab/train_colab_skeleton.ipynb`.
4. Click the key icon (**Secrets**), add `GITHUB_TOKEN`, paste the token, enable **Notebook access**.
   Never paste the token into a cell.
5. **Runtime > Change runtime type > A100 GPU** (needs a paid Colab plan; availability varies).
6. **Runtime > Run all**, and approve the Drive and Google sign-in prompts.
7. Success looks like: the GPU name is printed; a commit hash is printed; `checksum OK`; the contents of
   `version.json` appear; `env.json` is saved under `MyDrive/anpr/runs/<run id>/`.

| Problem | Fix |
|---|---|
| clone fails with 403 / not found | token expired, wrong repository, or notebook access off |
| `dataset_v5.zip not visible` | upload it to the folder, or share the folder with the Colab account |
| checksum mismatch | upload was incomplete; upload again |
| no A100 | choose another GPU for the smoke run and note it |
