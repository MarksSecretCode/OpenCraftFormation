(function () {
  "use strict";

  const NUMBER_FIELDS = new Set(["max_players", "root_volume_size_gb", "java_memory_mb"]);
  const CHECKBOX_FIELDS = new Set(["allocate_eip"]);
  const FIELD_IDS = [
    "server_type", "minecraft_version", "seed", "difficulty", "max_players", "motd",
    "instance_type", "root_volume_size_gb", "java_memory_mb",
    "ssh_cidr", "allocate_eip",
    "stack_name", "aws_profile", "region", "key_name", "vpc_id", "subnet_id",
  ];
  const ERROR_FIELDS = ["minecraft_version", "max_players", "java_memory_mb", "root_volume_size_gb", "ssh_cidr", "stack_name"];

  const state = {
    config: {},
    instanceOptions: [],
    maxReached: 1,
  };

  function $(id) { return document.getElementById(id); }
  function api() { return window.pywebview.api; }

  function humanSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // ---------------------------------------------------------------- nav --
  function goToScreen(n) {
    document.querySelectorAll(".screen").forEach((s) => { s.hidden = true; });
    $("screen-" + n).hidden = false;
    document.querySelectorAll("#steps li").forEach((li) => {
      const step = parseInt(li.dataset.step, 10);
      li.classList.toggle("active", step === n);
      li.classList.toggle("done", step < n);
    });
    state.maxReached = Math.max(state.maxReached, n);
    if (n === 2) initScreen2();
    if (n === 3) initScreen3();
  }

  function wireStepClicks() {
    document.querySelectorAll("#steps li").forEach((li) => {
      li.addEventListener("click", () => {
        const step = parseInt(li.dataset.step, 10);
        if (step <= state.maxReached) goToScreen(step);
      });
    });
  }

  // ------------------------------------------------------------ Screen 1 --
  function populateFormFromConfig() {
    FIELD_IDS.forEach((key) => {
      const el = $("f-" + key);
      if (!el) return;
      if (CHECKBOX_FIELDS.has(key)) {
        el.checked = !!state.config[key];
      } else {
        el.value = state.config[key] === undefined || state.config[key] === null ? "" : state.config[key];
      }
    });
  }

  function readFormIntoConfig() {
    FIELD_IDS.forEach((key) => {
      const el = $("f-" + key);
      if (!el) return;
      if (CHECKBOX_FIELDS.has(key)) {
        state.config[key] = el.checked;
      } else if (NUMBER_FIELDS.has(key)) {
        state.config[key] = parseInt(el.value, 10) || 0;
      } else {
        state.config[key] = el.value;
      }
    });
  }

  function clearErrors() {
    ERROR_FIELDS.forEach((key) => {
      const el = $("err-" + key);
      if (el) el.textContent = "";
    });
  }

  function showErrors(errors) {
    clearErrors();
    Object.keys(errors || {}).forEach((key) => {
      const el = $("err-" + key);
      if (el) el.textContent = errors[key];
    });
  }

  async function populateInstanceTypes() {
    state.instanceOptions = await api().instance_type_options();
    const sel = $("f-instance_type");
    sel.innerHTML = "";
    state.instanceOptions.forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt.type;
      o.textContent = opt.type + " — " + opt.vcpu + " vCPU / " + opt.memory_gb + " GB — ~$" + opt.hourly_usd.toFixed(4) + "/hr";
      sel.appendChild(o);
    });
    sel.value = state.config.instance_type || "t3.medium";
    updateMemSuggestion();
  }

  async function populateRegionList() {
    const regions = await api().common_regions();
    const list = $("region-list");
    list.innerHTML = "";
    regions.forEach((r) => {
      const o = document.createElement("option");
      o.value = r;
      list.appendChild(o);
    });
  }

  function updateMemSuggestion() {
    const opt = state.instanceOptions.find((o) => o.type === $("f-instance_type").value);
    const memField = $("f-java_memory_mb");
    if (!opt) { $("mem-suggest").textContent = ""; return; }
    const suggestedMb = Math.round((opt.memory_gb * 1024 * 0.7) / 256) * 256;
    $("mem-suggest").textContent = "suggested ~" + suggestedMb + " MB for this instance's " + opt.memory_gb + " GB RAM";
    if (!memField.value || memField.dataset.auto === "1") {
      memField.value = suggestedMb;
      memField.dataset.auto = "1";
    }
  }

  async function initScreen1() {
    state.config = await api().get_config();
    populateFormFromConfig();
    await populateInstanceTypes();
    await populateRegionList();
  }

  function wireScreen1Events() {
    $("f-instance_type").addEventListener("change", updateMemSuggestion);
    $("f-java_memory_mb").addEventListener("input", () => { delete $("f-java_memory_mb").dataset.auto; });

    $("btn-autofill-ip").addEventListener("click", async () => {
      const btn = $("btn-autofill-ip");
      btn.disabled = true;
      const res = await api().my_public_ip();
      btn.disabled = false;
      if (res.ok) {
        $("f-ssh_cidr").value = res.ip + "/32";
      } else {
        $("err-ssh_cidr").textContent = "Couldn't detect your IP: " + res.error;
      }
    });

    $("btn-1-next").addEventListener("click", async () => {
      readFormIntoConfig();
      const res = await api().save_config(state.config);
      if (!res.ok) {
        showErrors(res.errors);
        return;
      }
      clearErrors();
      goToScreen(2);
    });
  }

  // ------------------------------------------------------------ Screen 2 --
  function renderModsList(files) {
    const list = $("mods-list");
    list.innerHTML = "";
    if (files.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No files staged yet.";
      list.appendChild(li);
      return;
    }
    files.forEach((f) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = f.name;
      const size = document.createElement("span");
      size.className = "file-size";
      size.textContent = humanSize(f.size);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Remove";
      btn.addEventListener("click", async () => {
        const updated = await api().remove_mod(state.config.server_type, f.name);
        renderModsList(updated);
      });
      li.appendChild(name);
      li.appendChild(size);
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  function reportAddErrors(errors) {
    if (!errors || errors.length === 0) return;
    const messages = errors.map((e) => e.name + ": " + e.reason).join("\n");
    window.alert("Some files were skipped:\n" + messages);
  }

  async function refreshWorldStatus() {
    const count = await api().world_file_count();
    $("world-status").textContent = count > 0 ? count + " file(s) staged." : "No world files staged yet.";
  }

  async function refreshSpecialFiles() {
    const status = await api().special_files_status();
    document.querySelectorAll(".special-file-row").forEach((row) => {
      const name = row.dataset.name;
      const st = status[name] || { present: false, size: 0 };
      row.querySelector(".special-file-status").textContent = st.present
        ? "present (" + humanSize(st.size) + ")"
        : "not set";
    });
  }

  function wireScreen2Events() {
    const dropzone = $("dropzone");
    dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", async (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const files = Array.from(e.dataTransfer.files || []);
      const filePaths = files.map((f) => f.path).filter(Boolean);
      if (files.length > 0 && filePaths.length === 0) {
        $("dnd-hint").hidden = false;
        return;
      }
      $("dnd-hint").hidden = true;
      const res = await api().add_mods(state.config.server_type, filePaths);
      renderModsList(res.files);
      reportAddErrors(res.errors);
    });

    $("btn-browse-mods").addEventListener("click", async () => {
      const res = await api().browse_mods(state.config.server_type);
      renderModsList(res.files);
      reportAddErrors(res.errors);
    });
    $("btn-open-mods-folder").addEventListener("click", () => api().open_mods_folder(state.config.server_type));
    $("btn-open-world-folder").addEventListener("click", () => api().open_world_folder());
    $("btn-open-config-folder").addEventListener("click", () => api().open_config_folder());

    document.querySelectorAll(".browse-special").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const name = btn.closest(".special-file-row").dataset.name;
        await api().browse_special_file(name);
        refreshSpecialFiles();
      });
    });
    document.querySelectorAll(".remove-special").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const name = btn.closest(".special-file-row").dataset.name;
        await api().remove_special_file(name);
        refreshSpecialFiles();
      });
    });

    $("btn-2-back").addEventListener("click", () => goToScreen(1));
    $("btn-2-next").addEventListener("click", () => goToScreen(3));
  }

  async function initScreen2() {
    $("mods-heading").textContent = state.config.server_type === "Paper" ? "Plugins" : "Mods";
    const files = await api().list_mods(state.config.server_type);
    renderModsList(files);
    await refreshWorldStatus();
    await refreshSpecialFiles();
  }

  // ------------------------------------------------------------ Screen 3 --
  function summaryRow(dl, label, value) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  async function initScreen3() {
    readFormIntoConfig();
    const dl = $("summary");
    dl.innerHTML = "";
    const c = state.config;
    summaryRow(dl, "Server", c.server_type + " " + c.minecraft_version);
    summaryRow(dl, "Difficulty / Max players", c.difficulty + " / " + c.max_players);
    summaryRow(dl, "MOTD", c.motd || "(none)");
    summaryRow(dl, "Seed", c.seed || "(random)");
    summaryRow(dl, "Instance", c.instance_type + ", " + c.root_volume_size_gb + " GB root volume, " + c.java_memory_mb + " MB heap");
    summaryRow(dl, "Network", "SSH " + (c.ssh_cidr || "(disabled)") + (c.key_name ? " via " + c.key_name : " — no key pair set") + (c.allocate_eip ? ", static Elastic IP" : ""));
    summaryRow(dl, "AWS", (c.aws_profile || "(default profile)") + " / " + (c.region || "(default region)"));
    summaryRow(dl, "VPC / Subnet", (c.vpc_id || "(default VPC)") + " / " + (c.subnet_id || "(default subnet)"));

    const mods = await api().list_mods(c.server_type);
    const special = await api().special_files_status();
    const specialCount = Object.values(special).filter((s) => s.present).length;
    summaryRow(dl, (c.server_type === "Paper" ? "Plugins" : "Mods"), mods.length + " file(s)");
    summaryRow(dl, "Extra files", specialCount + " of 3 set (whitelist/ops/icon)");

    const cost = await api().estimate_cost(c.instance_type, c.root_volume_size_gb);
    const box = $("cost-box");
    if (cost.known) {
      box.textContent = "Estimated ~$" + cost.total_monthly_usd + "/month (~$" + cost.hourly_usd + "/hr compute + $" + cost.storage_monthly_usd + "/mo storage). " + cost.note;
    } else {
      box.textContent = "No cost estimate available for " + c.instance_type + ". " + cost.note;
    }

    $("export-error").hidden = true;
    $("export-result").hidden = true;
    $("btn-export").disabled = false;
  }

  function renderInstructions(instructions) {
    const ol = $("instructions");
    ol.innerHTML = "";
    instructions.forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      ol.appendChild(li);
    });
  }

  function wireScreen3Events() {
    $("btn-3-back").addEventListener("click", () => goToScreen(2));
    $("btn-export").addEventListener("click", async () => {
      $("btn-export").disabled = true;
      $("export-error").hidden = true;
      $("export-result").hidden = true;
      readFormIntoConfig();
      const res = await api().build_export(state.config);
      $("btn-export").disabled = false;
      if (!res.ok) {
        $("export-error").hidden = false;
        $("export-error").textContent = res.error || JSON.stringify(res.errors);
        return;
      }
      $("export-summary").textContent = "Built " + res.bundle_path + " (" + humanSize(res.bundle_size) + ", " + res.file_count + " files, including " + res.overlay_file_count + " from overlay/).";
      renderInstructions(res.instructions);
      $("export-result").hidden = false;
    });
    $("btn-open-build-folder").addEventListener("click", () => api().open_build_folder());
  }

  // ------------------------------------------------------------------ init --
  function init() {
    wireStepClicks();
    wireScreen1Events();
    wireScreen2Events();
    wireScreen3Events();
    initScreen1();
  }

  if (window.pywebview) {
    init();
  } else {
    window.addEventListener("pywebviewready", init);
  }
})();
