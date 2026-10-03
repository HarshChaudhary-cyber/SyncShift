import {test} from 'node:test';
import assert from 'node:assert/strict';
import {safeReturnUrl, verifySession} from '../lib/session-policy.mjs';
const user={user_id:1,email:'a@example.com'};
const memberships=[{id:1,role:'instructor'},{id:2,role:'learner'}];
test('only server profile and memberships establish a session',async()=>{
  const result=await verifySession(async()=>user,async()=>memberships);
  assert.equal(result.status,'authenticated');assert.deepEqual(result.memberships,memberships);
});
test('initial server or network errors do not fabricate an authenticated profile',async()=>{
  for(const error of [new TypeError('offline'),{status:500}]){
    const result=await verifySession(async()=>{throw error;},async()=>[]);
    assert.equal(result.status,'error');assert.equal(result.user,null);
  }
});
test('verified session survives a transient error and can retry',async()=>{
  const result=await verifySession(async()=>{throw {status:503};},async()=>[],{user,memberships});
  assert.equal(result.status,'authenticated');assert.equal(result.verified,false);assert.ok(result.error);
  assert.equal((await verifySession(async()=>user,async()=>memberships,result)).verified,true);
});
test('401 invalidates even a previously verified session',async()=>{
  const result=await verifySession(async()=>{throw {status:401};},async()=>[],{user,memberships});
  assert.equal(result.status,'unauthenticated');assert.equal(result.user,null);assert.deepEqual(result.memberships,[]);
});
test('membership failures cannot establish a new session',async()=>{
  const result=await verifySession(async()=>user,async()=>{throw {status:500};});assert.equal(result.status,'error');
});
test('invalid OAuth fallback profiles are rejected',async()=>{
  const result=await verifySession(async()=>({email:'claimed@example.com'}),async()=>memberships);assert.equal(result.status,'error');
});
test('internal return URLs are preserved, external and encoded redirects rejected',()=>{
  assert.equal(safeReturnUrl('/classes?invite=abc'),'/classes?invite=abc');
  for(const target of ['https://evil.example','//evil.example','/\\evil.example','/%2f%2fevil.example','/login','javascript:alert(1)','/\nevil',null]) assert.equal(safeReturnUrl(target),'/dashboard');
});
