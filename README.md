# CloneChat

The following features are expected:

**Main**
- Step 1: Dump the target (Channel/Group) messages content to a folder with `dump.db` file.
  ```shell
  python3 clonechat.py --input -100123456789 --output <output_folder_name>
  ```

- Step 2: Use the dumpped content to send this content to another telegram chat.
  ```shell
  python3 clonechat.py --input <output_folder_name> --output -100987654321
  ```

**Secondary**
- Do the steps above in oneline command (danger!):
  ```shell
  python3 clonechat --input -100123456789 --output -100987654321
  ```
