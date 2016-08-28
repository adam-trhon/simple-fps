#! /usr/bin/python2

import sys
from direct.showbase.ShowBase import ShowBase
from panda3d.core import PandaNode, NodePath, Camera, TextNode
from panda3d.core import Vec3, KeyboardButton
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionNode, CollisionSphere
from panda3d.core import CollisionRay, BitMask32, CollisionHandlerQueue
from panda3d.physics import ActorNode, ForceNode, LinearVectorForce
from panda3d.physics import PhysicsCollisionHandler
from direct.task import Task

# Before diving into this example, I *strongly* recommend
# to go through panda cheatsheets at
# https://www.panda3d.org/manual/index.php/Cheat_Sheets

# Right now it is all in one class. Perfectly sufficient for
# a small project like this.

class FPS(ShowBase):
	def __init__(self):

		ShowBase.__init__(self)

		# Load level. 
		# It must have
		# <Group> Cube { 
		#   <Collide> { Polyset keep descend } 
		# in the egg file
		# IMPORTANT: The name of the group matters for collisions.
		self.scene = self.loader.loadModel("level")
		self.scene.reparentTo(self.render)

		# Now we need player node.
		# Right now it is used only for camera, more in the future
		self.player = self.render.attachNewNode(PandaNode("player"))
		self.player.setPos(0, 0, 2.5)

		# Reparent camera to player so that it is rotated when player is
		self.camera.reparentTo(self.player)

		# Adjust camera lens
		pl =  self.cam.node().getLens()
		pl.setFov(70)
		pl.setNearFar(0.3, 300)
		self.cam.node().setLens(pl)

		# Exit when escape is pressed
        	self.accept("escape", sys.exit)

		# Set up physics
		self.setupHandmadePlayerPhysics()


	def setupHandmadePlayerPhysics(self):

		# Some default values (see frame update function
		# for their meaning)

		self.camH = 0
		self.camP = 0
		self.playerH = 0

		self.height = 1.8
		self.speed = 50

		self.vspeed = 0
		self.onGround = False
		self.direction = Vec3(0, 0, 0)

		# Setup collisions

		self.cTrav = CollisionTraverser()
		self.pusher = CollisionHandlerPusher()

		cn = CollisionNode('player')
		cn.addSolid(CollisionSphere(0,0,0,.5))
		solid = self.player.attachNewNode(cn)
		self.cTrav.addCollider(solid, base.pusher)
		self.pusher.addCollider(solid, self.player, self.drive.node())

		ray = CollisionRay()
		ray.setOrigin(0,0,-.2)
		ray.setDirection(0,0,-1)
		cn = CollisionNode('playerRay')
		cn.addSolid(ray)
		cn.setFromCollideMask(BitMask32.bit(0))
		cn.setIntoCollideMask(BitMask32.allOff())
		solid = self.player.attachNewNode(cn)
		self.nodeGroundHandler = CollisionHandlerQueue()
		self.cTrav.addCollider(solid, self.nodeGroundHandler)

		# Register frame update function

		self.taskMgr.add(self.handmadePlayerPhysicsFrameUpdate, "FrameUpdateTask")


	def handmadePlayerPhysicsFrameUpdate(self, task):

		# Read mouse and keyboard
		md = self.win.getPointer(0)
		if self.win.movePointer(0, self.win.getXSize()/2, self.win.getYSize()/2):
			dx = (md.getX() - self.win.getXSize()/2)*0.1
			dy = (md.getY() - self.win.getYSize()/2)*0.1
		else:
			dx = 0
			dy = 0

		# For such low-level functions it is better to use
		forwardButton = KeyboardButton.ascii_key('w')
		backwardButton = KeyboardButton.ascii_key('s')
		leftButton = KeyboardButton.ascii_key('a')
		rightButton = KeyboardButton.ascii_key('d')
		spaceKey = KeyboardButton.ascii_key(' ')
		lshift = KeyboardButton.lshift()
		isDown = base.mouseWatcherNode.is_button_down

		# Rotate camera ("head"). If on the ground, the rotation will
		# be used for player node ("body") instead of "head"
		self.camH = self.camH - dx
		self.camP = self.camP - dy;

		# Update only if on the ground, not when flying
		if self.onGround:

			# update speed
			if isDown(lshift):
				self.speed = 10
			else:
				self.speed = 5

			# compute new direction
			self.direction = Vec3(0, 0, 0)
			if isDown(forwardButton):
				self.direction = self.direction + Vec3.forward()
			if isDown(backwardButton):
				self.direction = self.direction + Vec3.back()
			if isDown(leftButton):
				self.direction = self.direction + Vec3.left()
			if isDown(rightButton):
				self.direction = self.direction + Vec3.right()
			if isDown(spaceKey):
				self.vspeed = 5

			# Allign "body" to "head"
			self.playerH = self.playerH + self.camH
			self.camH = 0

		self.camera.setPos(0, 0, 0) # because camera is player's child

		# Update rotations
		self.player.setH(self.playerH)
		self.camera.setH(self.camH)
		self.camera.setP(self.camP)

		# Apply direction to player position
		if self.direction.normalize():
			self.player.setPos(self.player, self.direction*self.speed*globalClock.getDt())

		# Finally, floor collisions. First find the highest plane below player.
		highestZ = -100
		for i in range(self.nodeGroundHandler.getNumEntries()):
			entry = self.nodeGroundHandler.getEntry(i)
			z = entry.getSurfacePoint(render).getZ()
			if z > highestZ and entry.getIntoNode().getName() == "Cube":
				highestZ = z

		# First handle free-fall. If the highest plane is below player or we are "falling" up (after jumping)...
		if (highestZ != -100 and highestZ < self.player.getZ()-self.height) or (self.vspeed > 0):
			print("falling:    "+str(self.player.getZ()-highestZ)) + " " + str(self.vspeed)
			# ... compute new player height ...
			newPlayerZ = self.player.getZ()+self.vspeed*globalClock.getDt()
			# ... and if new height is still above floor ...
			if newPlayerZ > highestZ+self.height:
				# ... move player to floor level and increase vertical speed.
				self.player.setZ(newPlayerZ)
				self.vspeed = self.vspeed - 9.81*globalClock.getDt()
				self.onGround = False

			# ... but if new height is below floor ...
			else:
				# ... put player right on the floor, but keep vertical speed.
				# Keeping vertical speed is needed to not jump when running down the hill
				self.player.setZ(highestZ+self.height)
				self.onGround = True

		# Now handle player slightly below floor, just by putting it to floor level and resetting vspeed
		# This can happen for example by arithmetic errors
		elif highestZ > self.player.getZ()-self.height:
			print("from under: "+str(self.player.getZ()-highestZ)) + " " + str(self.vspeed)
			self.player.setZ(highestZ+self.height)
			self.vspeed = 0
			self.onGround = True

		# Now the player is on the ground (first branch did not fire) but vspeed is not zero
		# This can happen when vspeed is kept in the first branch
		elif self.vspeed != 0:
			print("vspeed < 0: "+str(self.player.getZ()-highestZ)) + " " + str(self.vspeed)
			self.vspeed = 0
			self.onGround = True


		return task.cont

app = FPS()
app.run()


