using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

class SettingsTool : Form {
    TextBox blender = new TextBox(), status = new TextBox();
    CheckBox merge = new CheckBox();
    Button import = new Button(), export = new Button();
    public SettingsTool() {
        Text = "MZERMARTS — Réglages Power Importer";
        ClientSize = new Size(700, 390); MinimumSize = Size; StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10);
        var title = new Label { Text = "Sauvegarder ou restaurer la configuration de l’add-on", AutoSize = true, Location = new Point(18,18) };
        var hint = new Label { Text = "Choisissez blender.exe pour la version concernée (5.0 pour votre outil dédié).", AutoSize = true, Location = new Point(18,52) };
        blender.SetBounds(18,82,552,28);
        var browse = new Button { Text = "Parcourir…", Location = new Point(580,80), Size = new Size(103,30) };
        browse.Click += delegate { using(var d = new OpenFileDialog { Filter = "Blender|blender.exe", Title = "Choisir Blender" }) if(d.ShowDialog()==DialogResult.OK) blender.Text=d.FileName; };
        merge.Text = "Fusionner les bibliothèques lors de l’import"; merge.Checked=true; merge.SetBounds(18,126,650,28);
        import.Text="Importer un JSON…"; import.SetBounds(18,170,220,36);
        export.Text="Exporter vers un JSON…"; export.SetBounds(250,170,240,36);
        import.Click += async delegate { using(var d = new OpenFileDialog { Filter="Réglages JSON|*.json", Title="Choisir la sauvegarde à restaurer" }) if(d.ShowDialog()==DialogResult.OK) await Run(true,d.FileName,false); };
        export.Click += async delegate { using(var d = new SaveFileDialog { Filter="Réglages JSON|*.json", DefaultExt="json", AddExtension=true, FileName="power_importer.json", OverwritePrompt=true }) if(d.ShowDialog()==DialogResult.OK) await Run(false,d.FileName,File.Exists(d.FileName)); };
        status.Multiline=true; status.ReadOnly=true; status.ScrollBars=ScrollBars.Vertical; status.SetBounds(18,225,665,145);
        status.Text="Fermez Blender avant l’opération.\r\nExport : réglages déjà enregistrés. Import : préférences enregistrées pour la version choisie.\r\nLes modèles et journaux ne sont pas copiés. Aucun téléchargement ni indexation n’est lancé par cet utilitaire.";
        Controls.AddRange(new Control[]{ title,hint,blender,browse,merge,import,export,status });
        FormClosing += delegate(object s,FormClosingEventArgs e) { if(!import.Enabled) { e.Cancel=true; MessageBox.Show("Attendez la fin de l’opération."); } };
    }
    public static string Quote(string arg) {
        var b=new StringBuilder("\""); int slashes=0;
        foreach(char c in arg) { if(c=='\\') { slashes++; continue; } if(c=='\"') { b.Append('\\',slashes*2+1); b.Append(c); } else { b.Append('\\',slashes); b.Append(c); } slashes=0; }
        b.Append('\\',slashes*2); b.Append('"'); return b.ToString();
    }
    static string Embedded() { using(var s=Assembly.GetExecutingAssembly().GetManifestResourceStream("settings.py")) using(var r=new StreamReader(s,Encoding.UTF8)) return r.ReadToEnd(); }
    async Task Run(bool restoring,string path,bool overwrite) {
        try {
            if(!File.Exists(blender.Text) || !String.Equals(Path.GetFileName(blender.Text),"blender.exe",StringComparison.OrdinalIgnoreCase)) throw new Exception("Choisissez un fichier blender.exe existant.");
            if(Process.GetProcessesByName("blender").Length>0) throw new Exception("Fermez toutes les sessions Blender après sauvegarde du travail et des préférences, puis réessayez.");
            if(restoring && MessageBox.Show("Restaurer les réglages et enregistrer les préférences de cette version de Blender ?\n\n"+path+"\n\nMode : "+(merge.Checked?"fusion des bibliothèques":"remplacement de la configuration de l’add-on"),"Restaurer la configuration",MessageBoxButtons.OKCancel,MessageBoxIcon.Question)!=DialogResult.OK) return;
            import.Enabled=export.Enabled=false; status.Text="Opération en cours…";
            string folder=Path.Combine(Path.GetTempPath(),"MZERMARTS-PowerImporter",Guid.NewGuid().ToString("N")); Directory.CreateDirectory(folder);
            string script=Path.Combine(folder,"settings.py"); File.WriteAllText(script,Embedded(),new UTF8Encoding(false));
            string args="--background --disable-autoexec --python-exit-code 1 --python "+Quote(script)+" -- "+(restoring?"import":"export")+" "+Quote(path);
            if(restoring) args+=" --save-preferences"+(merge.Checked?" --merge":""); else if(overwrite) args+=" --overwrite";
            var info=new ProcessStartInfo(blender.Text,args) { UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8 };
            using(var process=Process.Start(info)) {
                Task<string> output=process.StandardOutput.ReadToEndAsync(), errors=process.StandardError.ReadToEndAsync();
                await Task.Run(()=>process.WaitForExit()); string result=await output+"\r\n"+await errors;
                File.WriteAllText(Path.Combine(folder,"execution.txt"),result,Encoding.UTF8);
                if(process.ExitCode!=0) throw new Exception("Blender signale un échec.\r\n"+result+"\r\nDiagnostic conservé : "+folder);
                status.Text=(restoring?"Réglages restaurés. Ouvrez Blender, contrôlez les chemins puis indexez manuellement.":"Sauvegarde créée : "+path)+"\r\nDiagnostic conservé : "+folder;
            }
        } catch(Exception e) { status.Text=e.Message; MessageBox.Show(e.Message,"Réglages Power Importer",MessageBoxButtons.OK,MessageBoxIcon.Warning); }
        finally { import.Enabled=export.Enabled=true; }
    }
    [STAThread] static int Main(string[] args) {
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        if(args.Length==1 && args[0]=="--self-test") {
            if(!Embedded().Contains("def import_settings") || Quote("a\\")!="\"a\\\\\"") return 1;
            using(var form=new SettingsTool()) { if(form.Controls.Count!=8) return 2; }
            return 0;
        }
        Application.Run(new SettingsTool()); return 0;
    }
}
