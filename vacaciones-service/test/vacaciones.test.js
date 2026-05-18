const request = require('supertest');
const app = require('../src/index');

describe('Vacaciones Service', () => {
  describe('GET /health', () => {
    it('should return 200 and status UP', async () => {
      const res = await request(app).get('/health');
      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('status', 'UP');
    });
  });

  describe('GET /vacaciones/:cedula', () => {
    it('should return 401 if no token provided', async () => {
      const res = await request(app).get('/vacaciones/12345');
      expect(res.statusCode).toEqual(401);
    });
  });
});
