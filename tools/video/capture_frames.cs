// Capture the frames of a TBIM workflow video from the open Revit model (Revit 2024+ API, C#).
//
// Run it with a C# script runner that calls McpDynamicScript.Run(UIApplication), e.g. the
// revit_send_code_to_revit tool of rvt-mcp, after the TBIM commands have produced their views:
//   Visualize > Model (InstanceBIM), Passage Graph, Data (cells, rl_HasLocation_tpZN), Types,
//   Data (faces, stFC_ThermalTransmittance).
// The frames go to %TEMP%\tbim_frames\<model name>####*.png with phases.txt; the model is saved at
// the end. Then compose the video with tools/video/video.py.
using System;
using System.Linq;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
public class McpDynamicScript {
 static string DIR;
 const int PX = 1280;
 static Document doc; static View3D v; static string PHASE;
 static BoundingBoxXYZ box;
 static string Uid(Element e) { var p = e.LookupParameter("UID"); return p == null ? "" : (p.AsString() ?? ""); }
 static double Z(Element e) { var b = e.get_BoundingBox(null); return b == null ? 0 : b.Min.Z; }
 static List<Element> Shapes(string tag) { return new FilteredElementCollector(doc).OfClass(typeof(DirectShape)).Where(e => ((DirectShape)e).ApplicationId == "TBIM" && ((DirectShape)e).ApplicationDataId == tag).OrderBy(Z).ToList(); }
 static List<Element> Of(params BuiltInCategory[] cats) { return new FilteredElementCollector(doc).WherePasses(new ElementMulticategoryFilter(cats.ToList())).WhereElementIsNotElementType().ToList(); }
 static List<Element> Hosts() { return Of(BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs).Where(e => Uid(e) != "").OrderBy(Z).ToList(); }
 static List<Element> Openings() { return Of(BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors).OrderBy(Z).ToList(); }
 static void Show(IEnumerable<Element> es) { var l = new List<ElementId>(es.Select(e => e.Id)); if (l.Count > 0) v.UnhideElements(l); }
 static void Hide(IEnumerable<Element> es) { var l = new List<ElementId>(es.Where(e => e.CanBeHidden(v)).Select(e => e.Id)); if (l.Count > 0) v.HideElements(l); }
 static void Ghost(int transparency, params BuiltInCategory[] cats) { var o = new OverrideGraphicSettings(); if (transparency > 0) { o.SetSurfaceTransparency(transparency); o.SetHalftone(true); } foreach (var c in cats) v.SetCategoryOverrides(new ElementId(c), o); }
 static void CopyOverrides(string fromView, IEnumerable<Element> es) { var src = new FilteredElementCollector(doc).OfClass(typeof(View3D)).Cast<View3D>().First(x => x.Name == fromView); foreach (var e in es) v.SetElementOverrides(e.Id, src.GetElementOverrides(e.Id)); }
 static void Clear(IEnumerable<Element> es) { foreach (var e in es) v.SetElementOverrides(e.Id, new OverrideGraphicSettings()); }
 static IEnumerable<List<T>> Steps<T>(List<T> l, int steps) { int n = Math.Max(1, (int)Math.Ceiling(l.Count / (double)steps)); for (int i = 0; i < l.Count; i += n) yield return l.Skip(i).Take(n).ToList(); }
 static void Orbit(double deg) {
   var c = (box.Min + box.Max) / 2;
   var f0 = new XYZ(1, 2, -1.2).Normalize(); var f = Transform.CreateRotation(XYZ.BasisZ, deg * Math.PI / 180).OfVector(f0);
   v.SetOrientation(new ViewOrientation3D(c - f * 1000, f.CrossProduct(XYZ.BasisZ).CrossProduct(f).Normalize(), f));
   doc.Regenerate();
   var tr = v.CropBox.Transform; var inv = tr.Inverse;
   var pts = new List<XYZ>(); foreach (var x in new[]{box.Min.X, box.Max.X}) foreach (var y in new[]{box.Min.Y, box.Max.Y}) foreach (var z in new[]{box.Min.Z, box.Max.Z}) pts.Add(inv.OfPoint(new XYZ(x, y, z)));
   double x0 = pts.Min(p => p.X), x1 = pts.Max(p => p.X), y0 = pts.Min(p => p.Y), y1 = pts.Max(p => p.Y);
   double cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, hw = (x1 - x0) / 2 * 1.08, hh = (y1 - y0) / 2 * 1.08;
   if (hw < hh * 16 / 9.0) hw = hh * 16 / 9.0; else hh = hw * 9 / 16.0;
   var bb = new BoundingBoxXYZ(); bb.Transform = tr; bb.Min = new XYZ(cx - hw, cy - hh, -5000); bb.Max = new XYZ(cx + hw, cy + hh, 5000); v.CropBox = bb;
 }
 static List<Action> Phase() {
   var s = new List<Action>(); Action hold = () => {};
   var model = Shapes("Model"); var faces = model.Where(e => !e.Name.StartsWith("window") && !e.Name.StartsWith("door")).ToList();
   var cells = Shapes("Data"); var graph = Shapes("Passage graph");
   // edges are named "<a>-<b> (<kind>)", nodes "<UID> (<zone>)" or "Exterior-<door UID>"
   var edges = graph.Where(e => System.Text.RegularExpressions.Regex.IsMatch(e.Name, @"\((door|wall|slab|stair|entrance)\)$")).ToList();
   var nodes = graph.Except(edges).ToList();
   var hosts = Hosts(); var openings = Openings();
   var H = new[]{BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs, BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors};
   switch (PHASE) {
     case "faces": foreach (var ch in Steps(faces, 24)) { var c = ch; s.Add(() => Show(c)); } for (int i = 0; i < 4; i++) s.Add(hold); break;
     case "controllers": s.Add(() => Hide(model)); foreach (var ch in Steps(hosts, 24)) { var c = ch; s.Add(() => Show(c)); } for (int i = 0; i < 4; i++) s.Add(hold); break;
     case "cells": s.Add(() => Ghost(80, H)); foreach (var ch in Steps(cells, 24)) { var c = ch; s.Add(() => Show(c)); } for (int i = 0; i < 4; i++) s.Add(hold); break;
     case "types": s.Add(() => { Hide(cells); Ghost(0, H); }); foreach (var ch in Steps(hosts, 16)) { var c = ch; s.Add(() => CopyOverrides("TBIM - Element types", c)); } for (int i = 0; i < 3; i++) s.Add(hold); break;
     case "apertures":
       foreach (var bic in new[]{BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors}) {
         var group = openings.Where(e => e.Category.Id.Value == (long)bic).ToList();
         foreach (var ch in Steps(group, 4)) { var c = ch; s.Add(() => { Show(c); CopyOverrides("TBIM - Element types", c); }); } s.Add(hold); }
       for (int i = 0; i < 3; i++) s.Add(hold); break;
     case "graph": s.Add(() => Ghost(85, H)); s.Add(() => Show(nodes)); foreach (var ch in Steps(edges, 20)) { var c = ch; s.Add(() => Show(c)); } for (int i = 0; i < 4; i++) s.Add(hold); break;
     case "data": s.Add(() => { Hide(graph); Ghost(0, H); CopyOverrides("TBIM - Faces by data", hosts); Clear(openings); }); for (int i = 0; i < 5; i++) s.Add(hold);
                  s.Add(() => { Clear(hosts); Clear(openings); }); for (int i = 0; i < 4; i++) s.Add(hold); break;
     case "orbit": for (int i = 1; i <= 72; i++) { var a = i * 5.0; s.Add(() => Orbit(a)); } break;
   }
   return s;
 }
 public static object Run(UIApplication app) {
  doc = app.ActiveUIDocument.Document;
  DIR = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "tbim_frames", System.IO.Path.GetFileNameWithoutExtension(doc.PathName));
  var theme = UIThemeManager.CurrentCanvasTheme; UIThemeManager.CurrentCanvasTheme = UITheme.Light;
  System.IO.Directory.CreateDirectory(DIR);
  foreach (var f in System.IO.Directory.GetFiles(DIR, "f*.png")) System.IO.File.Delete(f);
  var hosts = Hosts();
  box = new BoundingBoxXYZ(); double[] mn = {1e9,1e9,1e9}, mx = {-1e9,-1e9,-1e9};
  foreach (var e in hosts) { var b = e.get_BoundingBox(null); if (b == null) continue; mn[0] = Math.Min(mn[0], b.Min.X); mn[1] = Math.Min(mn[1], b.Min.Y); mn[2] = Math.Min(mn[2], b.Min.Z); mx[0] = Math.Max(mx[0], b.Max.X); mx[1] = Math.Max(mx[1], b.Max.Y); mx[2] = Math.Max(mx[2], b.Max.Z); }
  box.Min = new XYZ(mn[0], mn[1], mn[2]); box.Max = new XYZ(mx[0], mx[1], mx[2]);
  using (var t = new Transaction(doc, "TBIM video - setup")) { t.Start();
    v = new FilteredElementCollector(doc).OfClass(typeof(View3D)).Cast<View3D>().FirstOrDefault(x => x.Name == "Video");
    if (v != null) doc.Delete(v.Id);
    var vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>().First(x => x.ViewFamily == ViewFamily.ThreeDimensional);
    v = View3D.CreateIsometric(doc, vft.Id); v.Name = "Video";
    v.DisplayStyle = DisplayStyle.ShadingWithEdges; v.DetailLevel = ViewDetailLevel.Fine;
    v.CropBoxActive = true; v.CropBoxVisible = false;
    foreach (var c in new[]{BuiltInCategory.OST_MEPSpaces, BuiltInCategory.OST_Levels, BuiltInCategory.OST_Grids, BuiltInCategory.OST_GenericAnnotation, BuiltInCategory.OST_VolumeOfInterest, BuiltInCategory.OST_SectionBox, BuiltInCategory.OST_Cameras}) {
      var cat = Category.GetCategory(doc, c); if (cat != null && v.CanCategoryBeHidden(cat.Id)) v.SetCategoryHidden(cat.Id, true); }
    Hide(new FilteredElementCollector(doc).OfClass(typeof(DirectShape)).ToList()); Hide(hosts); Hide(Openings());
    Orbit(0); t.Commit(); }
  var log = new List<string>(); int frame = 0; var sw = System.Diagnostics.Stopwatch.StartNew();
  foreach (var phase in new[]{"faces","controllers","cells","types","apertures","graph","data","orbit"}) {
    PHASE = phase; var steps = Phase(); int first = frame;
    foreach (var step in steps) {
      using (var t = new Transaction(doc, "TBIM video - frame")) { t.Start(); step(); t.Commit(); }
      var o = new ImageExportOptions { ExportRange = ExportRange.SetOfViews, FilePath = System.IO.Path.Combine(DIR, "f" + frame.ToString("D4")), PixelSize = PX, ZoomType = ZoomFitType.FitToPage,
        HLRandWFViewsFileType = ImageFileType.PNG, ShadowViewsFileType = ImageFileType.PNG, ImageResolution = ImageResolution.DPI_150, FitDirection = FitDirectionType.Horizontal };
      o.SetViewsAndSheets(new List<ElementId>{ v.Id }); doc.ExportImage(o); frame++;
    }
    log.Add(phase + " " + first + "-" + (frame - 1));
  }
  System.IO.File.WriteAllLines(System.IO.Path.Combine(DIR, "phases.txt"), log);
  using (var t = new Transaction(doc, "TBIM video - reset")) { t.Start(); Ghost(0, BuiltInCategory.OST_Walls, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs, BuiltInCategory.OST_Windows, BuiltInCategory.OST_Doors); Orbit(0); t.Commit(); }
  UIThemeManager.CurrentCanvasTheme = theme;
  doc.Save();
  return string.Join("; ", log) + " in " + sw.Elapsed.TotalSeconds.ToString("0.0") + " s";
 }
}
