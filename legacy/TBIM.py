from topologicpy.CellComplex import CellComplex
from topologicpy.Plotly import Plotly
from topologicpy.Aperture import Aperture
from topologicpy.Face import Face
from topologicpy.Dictionary import Dictionary
from topologicpy.Topology import Topology
from topologicpy.Color import Color
from topologicpy.Cell import Cell
from topologicpy.Graph import Graph
import plotly.graph_objs as go

# Create Legend
def Plot_LegendTrace(color, label):
    return go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=10, color=color), name=label, showlegend=True)

# Plot Cells by textual key
def Plot_CellsByKey(cellComplex,
                       key="UID",keyType="str",
                       faceOpacity=0.2,camera=[1.5,1.5,1.5],target=[0,0,0],up=[0,0,1],
                       colorScale='inferno',unitsString="",
                       savePath=None):
    # White CellComplex
    dataList = []
    data = Plotly.DataByTopology(cellComplex, faceOpacity=faceOpacity, showVertexLegend=False, showEdgeLegend=False)
    dataList += data
    
    # Str Values
    if keyType == "str":
        # Values
        values = [Dictionary.ValueAtKey(Topology.Dictionary(_Cell), key) for _Cell in CellComplex.Cells(cellComplex)]
        values = sorted(list(set(values)))
        maxValue = len(values)
        values_numbers = [i for i in range(maxValue)]
        # Colors    
        color_labels = []   
        for _Cell in CellComplex.Cells(cellComplex):
            value = Dictionary.ValueAtKey(Topology.Dictionary(_Cell), key)
            valueNum = values_numbers[values.index(value)]
            color = Color.ByValueInRange(value=valueNum, minValue=0, maxValue=maxValue, colorScale="turbo")
            colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
            color_labels.append((colorStr, value))
            _Faces_bottomHorizontal = Cell.Decompose(_Cell)['bottomHorizontalFaces']
            for f in _Faces_bottomHorizontal:
                dataList += Plotly.DataByTopology(f, faceOpacity=1, faceColor=colorStr)
        color_labels = sorted(list(set(color_labels)),key=lambda x: x[1])
        # Legend
        legend_traces = [Plot_LegendTrace(color, label) for color, label in color_labels]
        legend_traces.insert(0, go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=0.1), name="<b>"+ key[0:]+"</b>", showlegend=True))
        dataList.extend(legend_traces)
        # Figure
        fig = Plotly.FigureByData(dataList)
        Plotly.SetCamera(fig, camera, target, up)
        Plotly.Show(fig)
    
    # Num Values    
    if keyType == "num":
        # Values
        values = []
        for _Cell in CellComplex.Cells(cellComplex):
            value = Dictionary.ValueAtKey(Topology.Dictionary(_Cell), key)
            values.append(value)
        maxValue = max(values)
        # Colors
        for _Cell in CellComplex.Cells(cellComplex):
            value = Dictionary.ValueAtKey(Topology.Dictionary(_Cell), key)
            color = Color.ByValueInRange(value=value, minValue=0, maxValue=maxValue, colorScale=colorScale)
            colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
            faces = Cell.Decompose(_Cell)['bottomHorizontalFaces']
            for f in faces:
                data = Plotly.DataByTopology(f, faceOpacity=1, faceColor=colorStr)
                dataList += data
        # Figure        
        fig = Plotly.FigureByData(dataList)
        colorBar = Plotly.AddColorBar(figure=fig,values=values,colorScale=colorScale,title=key[0:],nTicks=11,width=20,units=unitsString)
        Plotly.SetCamera(fig, camera, target, up)
        Plotly.Show(fig)
        if savePath:
            Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)
        
def Plot_FacesByKey(cellComplex,faces,
                       key="UID",keyType="str",
                       faceOpacity=0.2,camera=[1.5,1.5,1.5],target=[0,0,0],up=[0,0,1],
                       colorScale='inferno',unitsString="",showLegend=True,
                       savePath=None):
    # White CellComplex
    dataList = []
    data = Plotly.DataByTopology(cellComplex, faceOpacity=faceOpacity, showVertexLegend=False, showEdgeLegend=False)
    dataList += data
    
    # Str Values
    if keyType == "str":
        # Values
        values = [[Dictionary.ValueAtKey(Topology.Dictionary(face), key)][0] for face in faces]
        values = sorted(list(set(values)))
        maxValue = len(values)
        values_numbers = [i for i in range(maxValue)]
        # Colors    
        color_labels = []   
        for face in faces:
            value = Dictionary.ValueAtKey(Topology.Dictionary(face), key)
            valueNum = values_numbers[values.index(value)]
            color = Color.ByValueInRange(value=valueNum, minValue=0, maxValue=maxValue, colorScale="turbo")
            colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
            color_labels.append((colorStr, value))
            dataList += Plotly.DataByTopology(face, faceOpacity=1, faceColor=colorStr)
        color_labels = sorted(list(set(color_labels)),key=lambda x: x[1])
        # Legend
        legend_traces = [Plot_LegendTrace(color, label) for color, label in color_labels]
        legend_traces.insert(0, go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=0.1), name="<b>"+ key[0:]+"</b>", showlegend=True))
        dataList.extend(legend_traces)
        # Figure
        fig = Plotly.FigureByData(dataList)
        Plotly.SetCamera(fig, camera, target, up)
        Plotly.Show(fig)
        if savePath:
            Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)
    
    # Num Values    
    if keyType == "num":
        # Values
        values = []
        for face in faces:
            value = Dictionary.ValueAtKey(Topology.Dictionary(face), key)
            if isinstance(value,int) or isinstance(value,float):
                value = value
            else:
                value = 0 # None values
            values.append(value)
        maxValue = max(values)
        # Colors
        for face in faces:
            value = Dictionary.ValueAtKey(Topology.Dictionary(face), key)
            if isinstance(value,int) or isinstance(value,float):
                value = value
            else:
                value = 0 # None values
            color = Color.ByValueInRange(value=value, minValue=0, maxValue=maxValue, colorScale=colorScale)
            colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
            data = Plotly.DataByTopology(face, faceOpacity=1, faceColor=colorStr)
            dataList += data
        # Figure        
        fig = Plotly.FigureByData(dataList)
        if showLegend is True:
            colorBar = Plotly.AddColorBar(figure=fig,values=values,colorScale=colorScale,title=key[4:],nTicks=11,width=20,units=unitsString)
        Plotly.SetCamera(fig, camera, target, up)
        Plotly.Show(fig)
        Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)

def Plot_AperturesByKey(cellComplex,_Faces,_Face_PropName,savePath=None,camera=[1.5,1.5,1.5],target=[0,0,0],up=[0,0,1]):
    # White CellComplex
    
    dataList = []
    data = Plotly.DataByTopology(cellComplex, faceOpacity=0.2, showVertexLegend=False, showEdgeLegend=False)
    dataList += data
    # Values
    _Face_BetweenInformedSpace_Props = []
    _Apertures=[]
    for _Face in _Faces:
        for _Aperture in Topology.Apertures(_Face):
            _Apertures.append(_Aperture)
            _Face_Dictionary = Topology.Dictionary(_Aperture)
            _Face_BetweenInformedSpace_Prop = Dictionary.ValueAtKey(_Face_Dictionary, _Face_PropName)
            if _Face_BetweenInformedSpace_Prop is None:
                _Face_BetweenInformedSpace_Prop = 'Unknown'
            _Face_BetweenInformedSpace_Props.append(_Face_BetweenInformedSpace_Prop)
    _Face_BetweenInformedSpace_Props = sorted(list(set(_Face_BetweenInformedSpace_Props)))
    _Face_BetweenInformedSpace_Props_Number = [i for i in range(len(_Face_BetweenInformedSpace_Props))]
    # Colors
    color_labels = []
    for i, _Face_BetweenInformedSpace_Prop in enumerate(_Face_BetweenInformedSpace_Props):
        value = _Face_BetweenInformedSpace_Props_Number[i]
        color = Color.ByValueInRange(value=value, minValue=0, maxValue=len(_Face_BetweenInformedSpace_Props), colorScale="rainbow")
        colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
        color_labels.append((colorStr, _Face_BetweenInformedSpace_Prop))
        
    for _Face in _Apertures:
        _Face_Dictionary = Topology.Dictionary(_Face)
        _Face_BetweenInformedSpace_Prop = Dictionary.ValueAtKey(_Face_Dictionary, _Face_PropName)
        value = None

        if _Face_BetweenInformedSpace_Prop in _Face_BetweenInformedSpace_Props:
            index = _Face_BetweenInformedSpace_Props.index(_Face_BetweenInformedSpace_Prop)
            value = _Face_BetweenInformedSpace_Props_Number[index]
        else:
            value = 0

        color = Color.ByValueInRange(value=value, minValue=0, maxValue=len(_Face_BetweenInformedSpace_Props), colorScale="rainbow")
        colorStr = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")"
        
        apTop = Face.ByWire(Topology.Wires(_Face)[0])
        data = Plotly.DataByTopology(apTop, faceOpacity=1, faceColor=colorStr)
        dataList += data
    # Legend
    legend_traces = [Plot_LegendTrace(color, label) for color, label in color_labels]
    legend_traces.insert(0, go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=0.1), name="<b>"+ _Face_PropName[0:].replace("_pSP_",": ")+"</b>", showlegend=True))
    dataList.extend(legend_traces)
    # Figure
    fig = Plotly.FigureByData(dataList)
    Plotly.SetCamera(fig, camera, target, up)
    Plotly.Show(fig)
    if savePath:
        Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)
    
# Create Legend
def Plot_LegendTrace(color, label):
    return go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=10, color=color), name=label, showlegend=True)

# Create Legend
def Plot_LegendTrace(color, label):
    return go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=10, color=color), name=label, showlegend=True)

# Graph with faces
def Plot_AdjacencyGraph(cellComplex,colorScale="turbo",
                        savePath=None, vertexSize=1,
                        camera=[1.5,1.5,1.5],target=[0,0,0],up=[0,0,1],
                        edgeWidth=1):
    
    # Plot Graph - adjacency
    g = Graph.ByTopology(cellComplex, 
                         direct=False,
                         toExteriorTopologies=True,
                         viaSharedTopologies=True,
                         viaSharedApertures=False,
                         toExteriorApertures=False)

    d = CellComplex.Decompose(cellComplex)
    evf = d['externalVerticalFaces'] #1
    ivf = d['internalVerticalFaces'] #2
    thf = d['topHorizontalFaces'] #3
    bhf = d['bottomHorizontalFaces'] #4
    ihf = d['internalHorizontalFaces'] #5

    exterior_faces = evf+thf+bhf
    interior_faces = ivf+ihf
    cells = Topology.Cells(cellComplex)
    for cell in cells:
        dic = Dictionary.ByKeyValue("type",0)
        cell = Topology.SetDictionary(cell, dic)
    for f in evf:
        dic = Dictionary.ByKeyValue("type",1)
        f = Topology.SetDictionary(f, dic)
    for f in ivf:
        dic = Dictionary.ByKeyValue("type",2)
        f = Topology.SetDictionary(f, dic)
    for f in thf:
        dic = Dictionary.ByKeyValue("type",3)
        f = Topology.SetDictionary(f, dic)
    for f in bhf:
        dic = Dictionary.ByKeyValue("type",4)
        f = Topology.SetDictionary(f, dic)
    for f in ihf:
        dic = Dictionary.ByKeyValue("type",5)
        f = Topology.SetDictionary(f, dic)
        
    data02 = Plotly.DataByTopology(cellComplex, faceOpacity=0.2,edgeColor="gray",showVertices=False)
    data01 = Plotly.DataByGraph(g, 
                                vertexLabelKey="type", vertexGroupKey="type", vertexGroups=[0,1,2,3,4,5], 
                                colorScale='turbo',vertexSize=vertexSize,
                                edgeWidth=edgeWidth)
    fig = Plotly.FigureByData(data01+data02)
    
    Plotly.SetCamera(fig, camera, target, up)
    Plotly.Show(fig)
    Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)
    
# Graph with apertures
def Plot_PassageGraph(cellComplex,colorScale="turbo",vertexSize=1,savePath=None,camera=[1,1,1],target=[0,0,0],up=[0,0,1],edgeWidth=1):
    # Plot Graph - adjacency
    g = Graph.ByTopology(cellComplex, 
                         direct=False,
                         toExteriorTopologies=False,
                         viaSharedTopologies=False,
                         viaSharedApertures=True,
                         toExteriorApertures=True)

    c = cellComplex
    d = CellComplex.Decompose(c)
    
    cells = Topology.Cells(c)
    for cell in cells:
        dic = Dictionary.ByKeyValue("type",0)
        cell = Topology.SetDictionary(cell, dic)
    
    for f in CellComplex.Faces(c):
        for ap in Topology.Apertures(f):
            ap = ap
            d = Topology.Dictionary(ap)
            v = Dictionary.ValueAtKey(d,'pr_TopologicalType')
            if v == "door":
                dic = Dictionary.ByKeyValue("type",1)
                ap = Topology.SetDictionary(ap, dic)
            elif v == "window":
                dic = Dictionary.ByKeyValue("type",2)
                ap = Topology.SetDictionary(ap, dic)
            else:
                dic = Dictionary.ByKeyValue("type",3)
                ap = Topology.SetDictionary(ap, dic)
                
    
        
    data01 = Plotly.DataByGraph(g, edgeWidth=edgeWidth,vertexSize=vertexSize,vertexLabelKey="type", vertexGroupKey="type", vertexGroups=[0,1,2,3], colorScale=colorScale)
    data02 = Plotly.DataByTopology(c, faceOpacity=0.1)
    fig = Plotly.FigureByData(data01+data02)
    
    Plotly.SetCamera(fig, camera, target, up)
    Plotly.Show(fig)
    if savePath:
        Plotly.FigureExportToPNG(figure=fig,path=savePath,overwrite=True)