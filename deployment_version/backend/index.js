const fastify = require('fastify')({ logger: true });
const path = require('path');
const fs = require('fs');
const cors = require('fastify-cors');
const fastifyStatic = require('fastify-static');

fastify.register(cors, { origin: true });

fastify.register(fastifyStatic, {
  root: path.join(__dirname, '../../static/videos'),
  prefix: '/static/videos/',
  decorateReply: false
});

fastify.post('/chat', async (request, reply) => {
  const { message } = request.body || {};
  if (!message) {
    return reply.code(400).send({ error: 'No message provided' });
  }
  reply.send({ success: true, response: 'Placeholder chat response' });
});

fastify.post('/generate', async (request, reply) => {
  const { concept } = request.body || {};
  if (!concept) {
    return reply.code(400).send({ error: 'No concept provided' });
  }
  reply.send({ success: true, video_url: '/static/videos/placeholder.mp4', code: 'Placeholder manim code' });
});

fastify.get('/telegram-status', async (request, reply) => {
  reply.send({
    configured: false,
    bot_token_exists: false,
    chat_id_exists: false,
    bot_instance_exists: false
  });
});

fastify.post('/test-telegram', async (request, reply) => {
  reply.send({ success: true, message: 'Test notification sent successfully!' });
});

fastify.post('/update-docs', async (request, reply) => {
  reply.send({ success: true, message: 'Documentation updated successfully!', size: 0 });
});

fastify.setNotFoundHandler((request, reply) => {
  reply.code(404).send({ error: 'Not found' });
});

const start = async () => {
  try {
    await fastify.listen(5001, '0.0.0.0');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();