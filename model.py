import tensorflow as tf
from tensorflow import keras


class ProjectionLayer(keras.layers.Layer):
    def __init__(self, num_layers, output_size):
        super(ProjectionLayer, self).__init__()
        self.num_layers = num_layers
        self.output_size = output_size

    def build(self, input_shape):
        kernel_initializer = tf.random_normal_initializer(stddev=0.01)
        layers = []
        for _ in range(self.num_layers - 1):
            layers.append(keras.layers.Dense(input_shape[-1], kernel_initializer=kernel_initializer))
            layers.append(keras.layers.BatchNormalization())
            layers.append(keras.layers.Activation("relu"))
        layers.append(keras.layers.Dense(self.output_size, kernel_initializer=kernel_initializer, use_bias=False))
        layers.append(keras.layers.BatchNormalization(center=False))
        self.projection = keras.Sequential(layers)

    def call(self, input_tensor, training=None):
        return self.projection(input_tensor, training=training)


class ContrastiveModel(keras.Model):
    def __init__(self, backbone: keras.Model, projector: keras.layers.Layer, **kwargs):
        super(ContrastiveModel, self).__init__(**kwargs)
        self.backbone = backbone
        self.projector = projector

    def _forward(self, view1, view2, training):
        h1 = self.backbone(view1, training=training)
        h2 = self.backbone(view2, training=training)

        z1 = self.projector(h1, training=training)
        z2 = self.projector(h2, training=training)

        loss = self.compiled_loss(z1, z2)
        return loss

    def train_step(self, data):
        view1, view2 = data

        with tf.GradientTape() as tape:
            loss = self._forward(view1, view2, training=True)

        trainable_vars = self.trainable_variables
        gradients = tape.gradient(loss, trainable_vars)
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))

        return {m.name: m.result() for m in self.metrics}

    def test_step(self, data):
        view1, view2 = data
        self._forward(view1, view2, training=False)
        return {m.name: m.result() for m in self.metrics}


def contrastive_model():
    projector = ProjectionLayer(num_layers=2, output_size=256)
    backbone = keras.applications.resnet.ResNet50(weights=None, include_top=False, pooling="avg")
    return ContrastiveModel(backbone, projector)
