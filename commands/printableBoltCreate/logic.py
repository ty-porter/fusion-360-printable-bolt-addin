import adsk.core
import adsk.fusion
import math
import os
import json
import time

from .printable_bolt import PrintableBolt

app = adsk.core.Application.get()
ui = app.userInterface
skipValidate = False


class PrintableBoltLogic():
    def __init__(self, des: adsk.fusion.Design):
        # Read the cached values, if they exist.
        settings = None
        settingAttribute = des.attributes.itemByName('PrintableBolt', 'settings')
        if settingAttribute is not None:
            jsonSettings = settingAttribute.value
            settings = json.loads(jsonSettings)

        defaultUnits = des.unitsManager.defaultLengthUnits

        # Determine whether to use inches or millimeters as the initial default.
        if defaultUnits == 'in' or defaultUnits == 'ft':
            self.units = 'in'
        else:
            self.units = 'mm'

        # Define the default for each value and then check to see if there
        # were cached settings and override the default if a setting exists.
        if self.units == 'in':
            self.standard = 'English'
        else:
            self.standard = 'Metric'
        if settings:
            self.standard = settings['Standard']

        if self.standard == 'English':
            self.units = 'in'
        else:
            self.units = 'mm'

        # All these values should be in cm instead of mm even if set as units above
        # TODO: Read them from cache before defaulting
        self.shaftDiameter = '1.20'
        self.shaftLength = '2.4'

        self.backlash = '0.01'

        self.headHeight = '0.5'
        self.headDiameter = '2.0'

        self.headNumSides = '6'

        self.threadChamferDistance = '0.04'
        # TODO: Make configurable
        self.baseFilleted = True

        self.headless = False
        # TODO: Re-add head chamfer
        # self.headChamfered = False

    def CreateCommandInputs(self, inputs: adsk.core.CommandInputs):
        global skipValidate
        skipValidate = True

        # Create the command inputs to define the contents of the command dialog.
        self.standardDropDownInput = inputs.addDropDownCommandInput('standard', 'Standard', adsk.core.DropDownStyles.TextListDropDownStyle)
        if self.standard == "English":
            self.standardDropDownInput.listItems.add('English', True)
            self.standardDropDownInput.listItems.add('Metric', False)
        else:
            self.standardDropDownInput.listItems.add('English', False)
            self.standardDropDownInput.listItems.add('Metric', True)

        self.shaftDiameterValueInput = inputs.addValueInput('shaftDiameter', 'Shaft Diameter', self.units, adsk.core.ValueInput.createByReal(float(self.shaftDiameter)))
        self.shaftLengthValueInput = inputs.addValueInput('shaftLength', 'Shaft Length', self.units, adsk.core.ValueInput.createByReal(float(self.shaftLength)))

        self.backlashValueInput = inputs.addValueInput('backlash', 'Backlash', self.units, adsk.core.ValueInput.createByReal(float(self.backlash)))

        self.headDiameterValueInput = inputs.addValueInput('headDiameter', 'Head Diameter', self.units, adsk.core.ValueInput.createByReal(float(self.headDiameter)))
        self.headHeightValueInput = inputs.addValueInput('headHeight', 'Head Height', self.units, adsk.core.ValueInput.createByReal(float(self.headHeight)))

        self.headNumSidesInput = inputs.addStringValueInput('headNumSides', 'Head Number of Sides', str(self.headNumSides))

        self.threadChamferDistanceValueInput = inputs.addValueInput('threadChamferDistance', 'Thread Chamfer Distance', self.units, adsk.core.ValueInput.createByReal(float(self.threadChamferDistance)))
        self.baseFilletedBoolValueInput = inputs.addBoolValueInput('baseFilleted', 'Base Filleted', True, '', self.baseFilleted == True)

        self.headlessBoolValueInput = inputs.addBoolValueInput('headless', 'Headless', True, '', self.headless == True)
        # self.headChamferedBoolValueInput = inputs.addBoolValueInput('headChamfered', 'Head Chamfered', True, '', self.headChamfered == True)

        self.errorMessageTextInput = inputs.addTextBoxCommandInput('errMessage', '', '', 2, True)
        self.errorMessageTextInput.isFullWidth = True

        skipValidate = False

    def HandleValidateInputs(self, args: adsk.core.ValidateInputsEventArgs):
        if not skipValidate:
            self.errorMessageTextInput.text = ''

            # Shaft length and diameter > 0
            if not float(self.shaftLengthValueInput.value) > 0:
                self.errorMessageTextInput.text = 'The shaft length must be greater than 0.'
                args.areInputsValid = False
                return

            if not float(self.shaftDiameterValueInput.value) > 0:
                self.errorMessageTextInput.text = 'The shaft diameter must be greater than 0.'
                args.areInputsValid = False
                return

            # Thread chamfer distance >= 0
            if not float(self.threadChamferDistanceValueInput.value) >= 0:
                self.errorMessageTextInput.text = 'The thread chamfer distance value cannot be negative.'
                args.areInputsValid = False
                return

            # Backlash >= 0
            if not float(self.backlashValueInput.value) > 0:
                self.errorMessageTextInput.text = 'The backlash value cannot be negative.'
                args.areInputsValid = False
                return

            # Validations that should only happen if a head is desired:
            if bool(self.headlessBoolValueInput.value) == False:
                # Head height > 0
                if not float(self.headHeightValueInput.value) > 0:
                    self.errorMessageTextInput.text = 'The head height must be greater than 0.'
                    args.areInputsValid = False
                    return

                # Head diameter > 0
                if not float(self.headDiameterValueInput.value) > 0:
                    self.errorMessageTextInput.text = 'The head diameter must be greater than 0.'
                    args.areInputsValid = False
                    return

                # Head diameter > shaft diameter
                if not float(self.headDiameterValueInput.value) > float(self.shaftDiameterValueInput.value):
                    self.errorMessageTextInput.text = 'The head diameter must be greater than the shaft diameter.'
                    args.areInputsValid = False
                    return

                # Head number of sides > 2 and a whole number
                if not self.headNumSidesInput.value.isdigit() or int(self.headNumSidesInput.value) <= 2:
                    self.errorMessageTextInput.text = 'The number of sides must be a whole number greater than 2.'
                    args.areInputsValid = False
                    return

    def HandleInputsChanged(self, args: adsk.core.InputChangedEventArgs):
        changedInput = args.input

        if not skipValidate:
            if changedInput.id == 'standard':
                if self.standardDropDownInput.selectedItem.name == 'English':
                    self.units = 'in'
                elif self.standardDropDownInput.selectedItem.name == 'Metric':
                    self.units = 'mm'

            if changedInput.id == 'headless':
                if bool(self.headlessBoolValueInput.value) == True:
                    self.headDiameterValueInput.isVisible = False
                    self.headHeightValueInput.isVisible = False
                    self.headNumSidesInput.isVisible = False
                    # self.headChamferedBoolValueInput.isVisible = False

                    self.baseFilletedBoolValueInput.isVisible = False
                else:
                    self.headDiameterValueInput.isVisible = True
                    self.headHeightValueInput.isVisible = True
                    self.headNumSidesInput.isVisible = True
                    # self.headChamferedBoolValueInput.isVisible = True

                    self.baseFilletedBoolValueInput.isVisible = True

            # Set each one to it's current value to work around an issue where
            # otherwise if the user has edited the value, the value won't update
            # in the dialog because apparently it remembers the units when the
            # value was edited.  Setting the value using the API resets this.
            self.shaftDiameterValueInput.value = self.shaftDiameterValueInput.value
            self.shaftDiameterValueInput.unitType = self.units
            self.shaftLengthValueInput.value = self.shaftLengthValueInput.value
            self.shaftLengthValueInput.unitType = self.units
            self.threadChamferDistanceValueInput.value = self.threadChamferDistanceValueInput.value
            self.threadChamferDistanceValueInput.unitType = self.units
            self.backlashValueInput.value = self.backlashValueInput.value
            self.backlashValueInput.unitType = self.units
            self.headDiameterValueInput.value = self.headDiameterValueInput.value
            self.headDiameterValueInput.unitType = self.units
            self.headHeightValueInput.value = self.headHeightValueInput.value
            self.headHeightValueInput.unitType = self.units

    def HandleExecutePreview(self, args: adsk.core.CommandEventArgs):
        printable_bolt = PrintableBolt(ui, app)

        printable_bolt.bodyDiameter = float(self.shaftDiameterValueInput.value)
        printable_bolt.bodyLength = adsk.core.ValueInput.createByReal(float(self.shaftLengthValueInput.value))

        printable_bolt.headDiameter = float(self.headDiameterValueInput.value)
        printable_bolt.headHeight = float(self.headHeightValueInput.value)

        printable_bolt.headSides = int(self.headNumSidesInput.value) if not self.headlessBoolValueInput.value else 0

        printable_bolt.chamferDistance = adsk.core.ValueInput.createByReal(float(self.threadChamferDistanceValueInput.value))

        if not bool(self.baseFilletedBoolValueInput.value):
            printable_bolt.filletRadius = adsk.core.ValueInput.createByReal(0.0)

        printable_bolt.backlash = adsk.core.ValueInput.createByReal(float(self.backlashValueInput.value))

        printable_bolt.buildBolt()

    def HandleExecute(self, args: adsk.core.CommandEventArgs):
        printable_bolt = PrintableBolt(ui, app)

        printable_bolt.bodyDiameter = float(self.shaftDiameterValueInput.value)
        printable_bolt.bodyLength = adsk.core.ValueInput.createByReal(float(self.shaftLengthValueInput.value))

        printable_bolt.headDiameter = float(self.headDiameterValueInput.value)
        printable_bolt.headHeight = float(self.headHeightValueInput.value)

        printable_bolt.headSides = int(self.headNumSidesInput.value) if not self.headlessBoolValueInput.value else 0

        printable_bolt.chamferDistance = adsk.core.ValueInput.createByReal(float(self.threadChamferDistanceValueInput.value))

        if not bool(self.baseFilletedBoolValueInput.value):
            printable_bolt.filletRadius = adsk.core.ValueInput.createByReal(0.0)

        printable_bolt.backlash = adsk.core.ValueInput.createByReal(float(self.backlashValueInput.value))

        printable_bolt.buildBolt()