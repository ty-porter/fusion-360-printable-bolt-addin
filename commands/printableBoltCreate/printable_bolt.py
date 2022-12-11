import adsk.core, adsk.fusion, traceback, math
from ...lib import fusion360utils as futil

class PrintableBolt:
    def __init__(self, ui, app):
        defaultHeadDiameter    = 0.75
        defaultBodyDiameter    = 0.5
        defaultHeadHeight      = 0.3125
        defaultHeadSides       = 6
        defaultBodyLength      = 2.0
        defaultCutAngle        = 30.0 * (math.pi / 180)
        defaultChamferDistance = 0.03845
        defaultFilletRadius    = 0.02994
        defaultBacklash        = 0.0

        self.ui               = ui
        self.app              = app
        self._boltName        = 'Printable Bolt'
        self._headDiameter    = defaultHeadDiameter
        self._bodyDiameter    = defaultBodyDiameter
        self._headHeight      = defaultHeadHeight
        self._headSides       = defaultHeadSides
        self._bodyLength      = adsk.core.ValueInput.createByReal(defaultBodyLength)
        self._cutAngle        = defaultCutAngle
        self._chamferDistance = adsk.core.ValueInput.createByReal(defaultChamferDistance)
        self._filletRadius    = adsk.core.ValueInput.createByReal(defaultFilletRadius)
        self._backlash        = adsk.core.ValueInput.createByReal(defaultBacklash)

    #properties
    @property
    def boltName(self):
        return self._boltName
    @boltName.setter
    def boltName(self, value):
        self._boltName = value

    @property
    def headDiameter(self):
        return self._headDiameter
    @headDiameter.setter
    def headDiameter(self, value):
        self._headDiameter = value

    @property
    def bodyDiameter(self):
        return self._bodyDiameter
    @bodyDiameter.setter
    def bodyDiameter(self, value):
        self._bodyDiameter = value 

    @property
    def headHeight(self):
        return self._headHeight
    @headHeight.setter
    def headHeight(self, value):
        self._headHeight = value

    @property
    def headSides(self):
        return self._headSides
    @headSides.setter
    def headSides(self, value):
        self._headSides = value 

    @property
    def bodyLength(self):
        return self._bodyLength
    @bodyLength.setter
    def bodyLength(self, value):
        self._bodyLength = value   

    @property
    def cutAngle(self):
        return self._cutAngle
    @cutAngle.setter
    def cutAngle(self, value):
        self._cutAngle = value  

    @property
    def chamferDistance(self):
        return self._chamferDistance
    @chamferDistance.setter
    def chamferDistance(self, value):
        self._chamferDistance = value

    @property
    def filletRadius(self):
        return self._filletRadius
    @filletRadius.setter
    def filletRadius(self, value):
        self._filletRadius = value

    @property
    def backlash(self):
        return self._backlash
    @backlash.setter
    def backlash(self, value):
        self._backlash = value

    def createNewComponent(self):
        # Get the active design.
        product = self.app.activeProduct
        design = adsk.fusion.Design.cast(product)
        rootComp = design.rootComponent
        allOccs = rootComp.occurrences
        newOcc = allOccs.addNewComponent(adsk.core.Matrix3D.create())
        return newOcc.component

    def buildBolt(self):
        try:
            global newComp
            newComp = self.createNewComponent()
            if newComp is None:
                self.ui.messageBox('New component failed to create', 'New Component Failed')
                return

            # Create a new sketch.
            sketches = newComp.sketches
            xyPlane = newComp.xYConstructionPlane
            xzPlane = newComp.xZConstructionPlane
            sketch = sketches.add(xyPlane)
            center = adsk.core.Point3D.create(0, 0, 0)

            # Extrude a polygonal head
            if self.headSides > 0:
                vertices = []

                for i in range(0, self.headSides):
                    vertex = adsk.core.Point3D.create(
                        center.x + (self.headDiameter / 2) * math.cos(math.pi * i / (self.headSides / 2)),
                        center.y + (self.headDiameter / 2) * math.sin(math.pi * i / (self.headSides / 2)),
                        0
                    )
                    vertices.append(vertex)

                for i in range(0, self.headSides):
                    sketch.sketchCurves.sketchLines.addByTwoPoints(vertices[(i+1) % self.headSides], vertices[i])

                extrudes = newComp.features.extrudeFeatures
                prof = sketch.profiles[0]
                extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

                distance = adsk.core.ValueInput.createByReal(self.headHeight)
                extInput.setDistanceExtent(False, distance)
                headExt = extrudes.add(extInput)

            # Extrude a circular head to give the body a base
            else:
                sketch.sketchCurves.sketchCircles.addByCenterRadius(center, self.bodyDiameter / 100)

                extrudes = newComp.features.extrudeFeatures
                prof = sketch.profiles[0]
                extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

                distance = adsk.core.ValueInput.createByReal(self.headHeight)
                extInput.setDistanceExtent(False, distance)
                headExt = extrudes.add(extInput)

            fc = headExt.faces[1]
            bd = fc.body
            bd.name = self.boltName

            #create the body
            bodySketch = sketches.add(xyPlane)
            bodySketch.sketchCurves.sketchCircles.addByCenterRadius(center, self.bodyDiameter / 2)

            bodyProf = bodySketch.profiles[0]
            bodyExtInput = extrudes.createInput(bodyProf, adsk.fusion.FeatureOperations.JoinFeatureOperation)

            bodyExtInput.setAllExtent(adsk.fusion.ExtentDirections.NegativeExtentDirection)
            bodyExtInput.setDistanceExtent(False, self.bodyLength)
            bodyExt = extrudes.add(bodyExtInput)

            # create chamfer on head
            if False:
                edgeCol = adsk.core.ObjectCollection.create()
                edges = bodyExt.endFaces[0].edges
                for edgeI  in edges:
                    edgeCol.add(edgeI)

                chamferFeats = newComp.features.chamferFeatures
                chamferInput = chamferFeats.createInput(edgeCol, True)
                chamferInput.setToEqualDistance(self.chamferDistance)
                chamferFeats.add(chamferInput)

                # create fillet
                edgeCol.clear()
                loops = headExt.endFaces[0].loops
                edgeLoop = None
                for edgeLoop in loops:
                    #since there two edgeloops in the start face of head, one consists of one circle edge while the other six edges
                    if(len(edgeLoop.edges) == 1):
                        break

                edgeCol.add(edgeLoop.edges[0])  
                filletFeats = newComp.features.filletFeatures
                filletInput = filletFeats.createInput()
                filletInput.addConstantRadiusEdgeSet(edgeCol, self.filletRadius, True)
                filletFeats.add(filletInput)

                #create revolve feature 1
                revolveSketchOne = sketches.add(xzPlane)
                radius = self.headDiameter/2
                point1 = revolveSketchOne.modelToSketchSpace(adsk.core.Point3D.create(center.x + radius*math.cos(math.pi/6), 0, center.y))
                point2 = revolveSketchOne.modelToSketchSpace(adsk.core.Point3D.create(center.x + radius, 0, center.y))

                point3 = revolveSketchOne.modelToSketchSpace(adsk.core.Point3D.create(point2.x, 0, (point2.x - point1.x) * math.tan(self.cutAngle)))
                revolveSketchOne.sketchCurves.sketchLines.addByTwoPoints(point1, point2)
                revolveSketchOne.sketchCurves.sketchLines.addByTwoPoints(point2, point3)
                revolveSketchOne.sketchCurves.sketchLines.addByTwoPoints(point3, point1)

                #revolve feature 2
                revolveSketchTwo = sketches.add(xzPlane)
                point4 = revolveSketchTwo.modelToSketchSpace(adsk.core.Point3D.create(center.x + radius*math.cos(math.pi/6), 0, self.headHeight - center.y))
                point5 = revolveSketchTwo.modelToSketchSpace(adsk.core.Point3D.create(center.x + radius, 0, self.headHeight - center.y))
                point6 = revolveSketchTwo.modelToSketchSpace(adsk.core.Point3D.create(center.x + point2.x, 0, self.headHeight - center.y - (point5.x - point4.x) * math.tan(self.cutAngle)))
                revolveSketchTwo.sketchCurves.sketchLines.addByTwoPoints(point4, point5)
                revolveSketchTwo.sketchCurves.sketchLines.addByTwoPoints(point5, point6)
                revolveSketchTwo.sketchCurves.sketchLines.addByTwoPoints(point6, point4)

                zaxis = newComp.zConstructionAxis
                revolves = newComp.features.revolveFeatures
                revProf1 = revolveSketchTwo.profiles[0]
                revInput1 = revolves.createInput(revProf1, zaxis, adsk.fusion.FeatureOperations.CutFeatureOperation)

                revAngle = adsk.core.ValueInput.createByReal(math.pi*2)
                revInput1.setAngleExtent(False,revAngle)
                revolves.add(revInput1)

                revProf2 = revolveSketchOne.profiles[0]
                revInput2 = revolves.createInput(revProf2, zaxis, adsk.fusion.FeatureOperations.CutFeatureOperation)

                revInput2.setAngleExtent(False,revAngle)
                revolves.add(revInput2)
            
            sideFace = bodyExt.sideFaces[0]
            threads = newComp.features.threadFeatures
            threadDataQuery = threads.threadDataQuery
            defaultThreadType = threadDataQuery.defaultMetricThreadType
            recommendData = threadDataQuery.recommendThreadData(self.bodyDiameter, False, defaultThreadType)
            if recommendData[0]:
                threadInfo = threads.createThreadInfo(False, defaultThreadType, recommendData[1], recommendData[2])
                faces = adsk.core.ObjectCollection.create()
                faces.add(sideFace)
                threadInput = threads.createInput(faces, threadInfo)
                threadInput.isModeled = True
                threads.add(threadInput)
                threadFaces = threads[0].faces
                offsetFaces = adsk.core.ObjectCollection.create()

                for face in threadFaces:
                    offsetFaces.add(face)
                offsetFeatures = newComp.features.offsetFeatures
                offsetFaceFeatureInput = offsetFeatures.createInput(offsetFaces, adsk.core.ValueInput.createByReal(-0.1), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, False)

                offsetFeatures.add(offsetFaceFeatureInput)

        except:
            self.ui.messageBox(traceback.format_exc())