(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))r(o);new MutationObserver(o=>{for(const u of o)if(u.type==="childList")for(const c of u.addedNodes)c.tagName==="LINK"&&c.rel==="modulepreload"&&r(c)}).observe(document,{childList:!0,subtree:!0});function n(o){const u={};return o.integrity&&(u.integrity=o.integrity),o.referrerPolicy&&(u.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?u.credentials="include":o.crossOrigin==="anonymous"?u.credentials="omit":u.credentials="same-origin",u}function r(o){if(o.ep)return;o.ep=!0;const u=n(o);fetch(o.href,u)}})();function Um(s){return s&&s.__esModule&&Object.prototype.hasOwnProperty.call(s,"default")?s.default:s}var yc={exports:{}},ba={},Mc={exports:{}},pt={};/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var bp;function K_(){if(bp)return pt;bp=1;var s=Symbol.for("react.element"),e=Symbol.for("react.portal"),n=Symbol.for("react.fragment"),r=Symbol.for("react.strict_mode"),o=Symbol.for("react.profiler"),u=Symbol.for("react.provider"),c=Symbol.for("react.context"),d=Symbol.for("react.forward_ref"),p=Symbol.for("react.suspense"),m=Symbol.for("react.memo"),x=Symbol.for("react.lazy"),S=Symbol.iterator;function g(I){return I===null||typeof I!="object"?null:(I=S&&I[S]||I["@@iterator"],typeof I=="function"?I:null)}var y={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},M=Object.assign,C={};function _(I,j,Ce){this.props=I,this.context=j,this.refs=C,this.updater=Ce||y}_.prototype.isReactComponent={},_.prototype.setState=function(I,j){if(typeof I!="object"&&typeof I!="function"&&I!=null)throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");this.updater.enqueueSetState(this,I,j,"setState")},_.prototype.forceUpdate=function(I){this.updater.enqueueForceUpdate(this,I,"forceUpdate")};function v(){}v.prototype=_.prototype;function R(I,j,Ce){this.props=I,this.context=j,this.refs=C,this.updater=Ce||y}var L=R.prototype=new v;L.constructor=R,M(L,_.prototype),L.isPureReactComponent=!0;var b=Array.isArray,F=Object.prototype.hasOwnProperty,U={current:null},z={key:!0,ref:!0,__self:!0,__source:!0};function A(I,j,Ce){var Xe,Ze={},ie=null,me=null;if(j!=null)for(Xe in j.ref!==void 0&&(me=j.ref),j.key!==void 0&&(ie=""+j.key),j)F.call(j,Xe)&&!z.hasOwnProperty(Xe)&&(Ze[Xe]=j[Xe]);var pe=arguments.length-2;if(pe===1)Ze.children=Ce;else if(1<pe){for(var Fe=Array(pe),He=0;He<pe;He++)Fe[He]=arguments[He+2];Ze.children=Fe}if(I&&I.defaultProps)for(Xe in pe=I.defaultProps,pe)Ze[Xe]===void 0&&(Ze[Xe]=pe[Xe]);return{$$typeof:s,type:I,key:ie,ref:me,props:Ze,_owner:U.current}}function D(I,j){return{$$typeof:s,type:I.type,key:j,ref:I.ref,props:I.props,_owner:I._owner}}function fe(I){return typeof I=="object"&&I!==null&&I.$$typeof===s}function O(I){var j={"=":"=0",":":"=2"};return"$"+I.replace(/[=:]/g,function(Ce){return j[Ce]})}var te=/\/+/g;function Q(I,j){return typeof I=="object"&&I!==null&&I.key!=null?O(""+I.key):j.toString(36)}function oe(I,j,Ce,Xe,Ze){var ie=typeof I;(ie==="undefined"||ie==="boolean")&&(I=null);var me=!1;if(I===null)me=!0;else switch(ie){case"string":case"number":me=!0;break;case"object":switch(I.$$typeof){case s:case e:me=!0}}if(me)return me=I,Ze=Ze(me),I=Xe===""?"."+Q(me,0):Xe,b(Ze)?(Ce="",I!=null&&(Ce=I.replace(te,"$&/")+"/"),oe(Ze,j,Ce,"",function(He){return He})):Ze!=null&&(fe(Ze)&&(Ze=D(Ze,Ce+(!Ze.key||me&&me.key===Ze.key?"":(""+Ze.key).replace(te,"$&/")+"/")+I)),j.push(Ze)),1;if(me=0,Xe=Xe===""?".":Xe+":",b(I))for(var pe=0;pe<I.length;pe++){ie=I[pe];var Fe=Xe+Q(ie,pe);me+=oe(ie,j,Ce,Fe,Ze)}else if(Fe=g(I),typeof Fe=="function")for(I=Fe.call(I),pe=0;!(ie=I.next()).done;)ie=ie.value,Fe=Xe+Q(ie,pe++),me+=oe(ie,j,Ce,Fe,Ze);else if(ie==="object")throw j=String(I),Error("Objects are not valid as a React child (found: "+(j==="[object Object]"?"object with keys {"+Object.keys(I).join(", ")+"}":j)+"). If you meant to render a collection of children, use an array instead.");return me}function K(I,j,Ce){if(I==null)return I;var Xe=[],Ze=0;return oe(I,Xe,"","",function(ie){return j.call(Ce,ie,Ze++)}),Xe}function ee(I){if(I._status===-1){var j=I._result;j=j(),j.then(function(Ce){(I._status===0||I._status===-1)&&(I._status=1,I._result=Ce)},function(Ce){(I._status===0||I._status===-1)&&(I._status=2,I._result=Ce)}),I._status===-1&&(I._status=0,I._result=j)}if(I._status===1)return I._result.default;throw I._result}var W={current:null},q={transition:null},ae={ReactCurrentDispatcher:W,ReactCurrentBatchConfig:q,ReactCurrentOwner:U};function le(){throw Error("act(...) is not supported in production builds of React.")}return pt.Children={map:K,forEach:function(I,j,Ce){K(I,function(){j.apply(this,arguments)},Ce)},count:function(I){var j=0;return K(I,function(){j++}),j},toArray:function(I){return K(I,function(j){return j})||[]},only:function(I){if(!fe(I))throw Error("React.Children.only expected to receive a single React element child.");return I}},pt.Component=_,pt.Fragment=n,pt.Profiler=o,pt.PureComponent=R,pt.StrictMode=r,pt.Suspense=p,pt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=ae,pt.act=le,pt.cloneElement=function(I,j,Ce){if(I==null)throw Error("React.cloneElement(...): The argument must be a React element, but you passed "+I+".");var Xe=M({},I.props),Ze=I.key,ie=I.ref,me=I._owner;if(j!=null){if(j.ref!==void 0&&(ie=j.ref,me=U.current),j.key!==void 0&&(Ze=""+j.key),I.type&&I.type.defaultProps)var pe=I.type.defaultProps;for(Fe in j)F.call(j,Fe)&&!z.hasOwnProperty(Fe)&&(Xe[Fe]=j[Fe]===void 0&&pe!==void 0?pe[Fe]:j[Fe])}var Fe=arguments.length-2;if(Fe===1)Xe.children=Ce;else if(1<Fe){pe=Array(Fe);for(var He=0;He<Fe;He++)pe[He]=arguments[He+2];Xe.children=pe}return{$$typeof:s,type:I.type,key:Ze,ref:ie,props:Xe,_owner:me}},pt.createContext=function(I){return I={$$typeof:c,_currentValue:I,_currentValue2:I,_threadCount:0,Provider:null,Consumer:null,_defaultValue:null,_globalName:null},I.Provider={$$typeof:u,_context:I},I.Consumer=I},pt.createElement=A,pt.createFactory=function(I){var j=A.bind(null,I);return j.type=I,j},pt.createRef=function(){return{current:null}},pt.forwardRef=function(I){return{$$typeof:d,render:I}},pt.isValidElement=fe,pt.lazy=function(I){return{$$typeof:x,_payload:{_status:-1,_result:I},_init:ee}},pt.memo=function(I,j){return{$$typeof:m,type:I,compare:j===void 0?null:j}},pt.startTransition=function(I){var j=q.transition;q.transition={};try{I()}finally{q.transition=j}},pt.unstable_act=le,pt.useCallback=function(I,j){return W.current.useCallback(I,j)},pt.useContext=function(I){return W.current.useContext(I)},pt.useDebugValue=function(){},pt.useDeferredValue=function(I){return W.current.useDeferredValue(I)},pt.useEffect=function(I,j){return W.current.useEffect(I,j)},pt.useId=function(){return W.current.useId()},pt.useImperativeHandle=function(I,j,Ce){return W.current.useImperativeHandle(I,j,Ce)},pt.useInsertionEffect=function(I,j){return W.current.useInsertionEffect(I,j)},pt.useLayoutEffect=function(I,j){return W.current.useLayoutEffect(I,j)},pt.useMemo=function(I,j){return W.current.useMemo(I,j)},pt.useReducer=function(I,j,Ce){return W.current.useReducer(I,j,Ce)},pt.useRef=function(I){return W.current.useRef(I)},pt.useState=function(I){return W.current.useState(I)},pt.useSyncExternalStore=function(I,j,Ce){return W.current.useSyncExternalStore(I,j,Ce)},pt.useTransition=function(){return W.current.useTransition()},pt.version="18.3.1",pt}var Pp;function Jf(){return Pp||(Pp=1,Mc.exports=K_()),Mc.exports}/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Dp;function Z_(){if(Dp)return ba;Dp=1;var s=Jf(),e=Symbol.for("react.element"),n=Symbol.for("react.fragment"),r=Object.prototype.hasOwnProperty,o=s.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,u={key:!0,ref:!0,__self:!0,__source:!0};function c(d,p,m){var x,S={},g=null,y=null;m!==void 0&&(g=""+m),p.key!==void 0&&(g=""+p.key),p.ref!==void 0&&(y=p.ref);for(x in p)r.call(p,x)&&!u.hasOwnProperty(x)&&(S[x]=p[x]);if(d&&d.defaultProps)for(x in p=d.defaultProps,p)S[x]===void 0&&(S[x]=p[x]);return{$$typeof:e,type:d,key:g,ref:y,props:S,_owner:o.current}}return ba.Fragment=n,ba.jsx=c,ba.jsxs=c,ba}var Lp;function Q_(){return Lp||(Lp=1,yc.exports=Z_()),yc.exports}var he=Q_(),Qt=Jf();const J_=Um(Qt);var tl={},Ec={exports:{}},Ln={},Tc={exports:{}},wc={};/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Np;function e0(){return Np||(Np=1,(function(s){function e(q,ae){var le=q.length;q.push(ae);e:for(;0<le;){var I=le-1>>>1,j=q[I];if(0<o(j,ae))q[I]=ae,q[le]=j,le=I;else break e}}function n(q){return q.length===0?null:q[0]}function r(q){if(q.length===0)return null;var ae=q[0],le=q.pop();if(le!==ae){q[0]=le;e:for(var I=0,j=q.length,Ce=j>>>1;I<Ce;){var Xe=2*(I+1)-1,Ze=q[Xe],ie=Xe+1,me=q[ie];if(0>o(Ze,le))ie<j&&0>o(me,Ze)?(q[I]=me,q[ie]=le,I=ie):(q[I]=Ze,q[Xe]=le,I=Xe);else if(ie<j&&0>o(me,le))q[I]=me,q[ie]=le,I=ie;else break e}}return ae}function o(q,ae){var le=q.sortIndex-ae.sortIndex;return le!==0?le:q.id-ae.id}if(typeof performance=="object"&&typeof performance.now=="function"){var u=performance;s.unstable_now=function(){return u.now()}}else{var c=Date,d=c.now();s.unstable_now=function(){return c.now()-d}}var p=[],m=[],x=1,S=null,g=3,y=!1,M=!1,C=!1,_=typeof setTimeout=="function"?setTimeout:null,v=typeof clearTimeout=="function"?clearTimeout:null,R=typeof setImmediate<"u"?setImmediate:null;typeof navigator<"u"&&navigator.scheduling!==void 0&&navigator.scheduling.isInputPending!==void 0&&navigator.scheduling.isInputPending.bind(navigator.scheduling);function L(q){for(var ae=n(m);ae!==null;){if(ae.callback===null)r(m);else if(ae.startTime<=q)r(m),ae.sortIndex=ae.expirationTime,e(p,ae);else break;ae=n(m)}}function b(q){if(C=!1,L(q),!M)if(n(p)!==null)M=!0,ee(F);else{var ae=n(m);ae!==null&&W(b,ae.startTime-q)}}function F(q,ae){M=!1,C&&(C=!1,v(A),A=-1),y=!0;var le=g;try{for(L(ae),S=n(p);S!==null&&(!(S.expirationTime>ae)||q&&!O());){var I=S.callback;if(typeof I=="function"){S.callback=null,g=S.priorityLevel;var j=I(S.expirationTime<=ae);ae=s.unstable_now(),typeof j=="function"?S.callback=j:S===n(p)&&r(p),L(ae)}else r(p);S=n(p)}if(S!==null)var Ce=!0;else{var Xe=n(m);Xe!==null&&W(b,Xe.startTime-ae),Ce=!1}return Ce}finally{S=null,g=le,y=!1}}var U=!1,z=null,A=-1,D=5,fe=-1;function O(){return!(s.unstable_now()-fe<D)}function te(){if(z!==null){var q=s.unstable_now();fe=q;var ae=!0;try{ae=z(!0,q)}finally{ae?Q():(U=!1,z=null)}}else U=!1}var Q;if(typeof R=="function")Q=function(){R(te)};else if(typeof MessageChannel<"u"){var oe=new MessageChannel,K=oe.port2;oe.port1.onmessage=te,Q=function(){K.postMessage(null)}}else Q=function(){_(te,0)};function ee(q){z=q,U||(U=!0,Q())}function W(q,ae){A=_(function(){q(s.unstable_now())},ae)}s.unstable_IdlePriority=5,s.unstable_ImmediatePriority=1,s.unstable_LowPriority=4,s.unstable_NormalPriority=3,s.unstable_Profiling=null,s.unstable_UserBlockingPriority=2,s.unstable_cancelCallback=function(q){q.callback=null},s.unstable_continueExecution=function(){M||y||(M=!0,ee(F))},s.unstable_forceFrameRate=function(q){0>q||125<q?console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"):D=0<q?Math.floor(1e3/q):5},s.unstable_getCurrentPriorityLevel=function(){return g},s.unstable_getFirstCallbackNode=function(){return n(p)},s.unstable_next=function(q){switch(g){case 1:case 2:case 3:var ae=3;break;default:ae=g}var le=g;g=ae;try{return q()}finally{g=le}},s.unstable_pauseExecution=function(){},s.unstable_requestPaint=function(){},s.unstable_runWithPriority=function(q,ae){switch(q){case 1:case 2:case 3:case 4:case 5:break;default:q=3}var le=g;g=q;try{return ae()}finally{g=le}},s.unstable_scheduleCallback=function(q,ae,le){var I=s.unstable_now();switch(typeof le=="object"&&le!==null?(le=le.delay,le=typeof le=="number"&&0<le?I+le:I):le=I,q){case 1:var j=-1;break;case 2:j=250;break;case 5:j=1073741823;break;case 4:j=1e4;break;default:j=5e3}return j=le+j,q={id:x++,callback:ae,priorityLevel:q,startTime:le,expirationTime:j,sortIndex:-1},le>I?(q.sortIndex=le,e(m,q),n(p)===null&&q===n(m)&&(C?(v(A),A=-1):C=!0,W(b,le-I))):(q.sortIndex=j,e(p,q),M||y||(M=!0,ee(F))),q},s.unstable_shouldYield=O,s.unstable_wrapCallback=function(q){var ae=g;return function(){var le=g;g=ae;try{return q.apply(this,arguments)}finally{g=le}}}})(wc)),wc}var Ip;function t0(){return Ip||(Ip=1,Tc.exports=e0()),Tc.exports}/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Up;function n0(){if(Up)return Ln;Up=1;var s=Jf(),e=t0();function n(t){for(var i="https://reactjs.org/docs/error-decoder.html?invariant="+t,a=1;a<arguments.length;a++)i+="&args[]="+encodeURIComponent(arguments[a]);return"Minified React error #"+t+"; visit "+i+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}var r=new Set,o={};function u(t,i){c(t,i),c(t+"Capture",i)}function c(t,i){for(o[t]=i,t=0;t<i.length;t++)r.add(i[t])}var d=!(typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"),p=Object.prototype.hasOwnProperty,m=/^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,x={},S={};function g(t){return p.call(S,t)?!0:p.call(x,t)?!1:m.test(t)?S[t]=!0:(x[t]=!0,!1)}function y(t,i,a,l){if(a!==null&&a.type===0)return!1;switch(typeof i){case"function":case"symbol":return!0;case"boolean":return l?!1:a!==null?!a.acceptsBooleans:(t=t.toLowerCase().slice(0,5),t!=="data-"&&t!=="aria-");default:return!1}}function M(t,i,a,l){if(i===null||typeof i>"u"||y(t,i,a,l))return!0;if(l)return!1;if(a!==null)switch(a.type){case 3:return!i;case 4:return i===!1;case 5:return isNaN(i);case 6:return isNaN(i)||1>i}return!1}function C(t,i,a,l,f,h,T){this.acceptsBooleans=i===2||i===3||i===4,this.attributeName=l,this.attributeNamespace=f,this.mustUseProperty=a,this.propertyName=t,this.type=i,this.sanitizeURL=h,this.removeEmptyString=T}var _={};"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(t){_[t]=new C(t,0,!1,t,null,!1,!1)}),[["acceptCharset","accept-charset"],["className","class"],["htmlFor","for"],["httpEquiv","http-equiv"]].forEach(function(t){var i=t[0];_[i]=new C(i,1,!1,t[1],null,!1,!1)}),["contentEditable","draggable","spellCheck","value"].forEach(function(t){_[t]=new C(t,2,!1,t.toLowerCase(),null,!1,!1)}),["autoReverse","externalResourcesRequired","focusable","preserveAlpha"].forEach(function(t){_[t]=new C(t,2,!1,t,null,!1,!1)}),"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(t){_[t]=new C(t,3,!1,t.toLowerCase(),null,!1,!1)}),["checked","multiple","muted","selected"].forEach(function(t){_[t]=new C(t,3,!0,t,null,!1,!1)}),["capture","download"].forEach(function(t){_[t]=new C(t,4,!1,t,null,!1,!1)}),["cols","rows","size","span"].forEach(function(t){_[t]=new C(t,6,!1,t,null,!1,!1)}),["rowSpan","start"].forEach(function(t){_[t]=new C(t,5,!1,t.toLowerCase(),null,!1,!1)});var v=/[\-:]([a-z])/g;function R(t){return t[1].toUpperCase()}"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(t){var i=t.replace(v,R);_[i]=new C(i,1,!1,t,null,!1,!1)}),"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(t){var i=t.replace(v,R);_[i]=new C(i,1,!1,t,"http://www.w3.org/1999/xlink",!1,!1)}),["xml:base","xml:lang","xml:space"].forEach(function(t){var i=t.replace(v,R);_[i]=new C(i,1,!1,t,"http://www.w3.org/XML/1998/namespace",!1,!1)}),["tabIndex","crossOrigin"].forEach(function(t){_[t]=new C(t,1,!1,t.toLowerCase(),null,!1,!1)}),_.xlinkHref=new C("xlinkHref",1,!1,"xlink:href","http://www.w3.org/1999/xlink",!0,!1),["src","href","action","formAction"].forEach(function(t){_[t]=new C(t,1,!1,t.toLowerCase(),null,!0,!0)});function L(t,i,a,l){var f=_.hasOwnProperty(i)?_[i]:null;(f!==null?f.type!==0:l||!(2<i.length)||i[0]!=="o"&&i[0]!=="O"||i[1]!=="n"&&i[1]!=="N")&&(M(i,a,f,l)&&(a=null),l||f===null?g(i)&&(a===null?t.removeAttribute(i):t.setAttribute(i,""+a)):f.mustUseProperty?t[f.propertyName]=a===null?f.type===3?!1:"":a:(i=f.attributeName,l=f.attributeNamespace,a===null?t.removeAttribute(i):(f=f.type,a=f===3||f===4&&a===!0?"":""+a,l?t.setAttributeNS(l,i,a):t.setAttribute(i,a))))}var b=s.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,F=Symbol.for("react.element"),U=Symbol.for("react.portal"),z=Symbol.for("react.fragment"),A=Symbol.for("react.strict_mode"),D=Symbol.for("react.profiler"),fe=Symbol.for("react.provider"),O=Symbol.for("react.context"),te=Symbol.for("react.forward_ref"),Q=Symbol.for("react.suspense"),oe=Symbol.for("react.suspense_list"),K=Symbol.for("react.memo"),ee=Symbol.for("react.lazy"),W=Symbol.for("react.offscreen"),q=Symbol.iterator;function ae(t){return t===null||typeof t!="object"?null:(t=q&&t[q]||t["@@iterator"],typeof t=="function"?t:null)}var le=Object.assign,I;function j(t){if(I===void 0)try{throw Error()}catch(a){var i=a.stack.trim().match(/\n( *(at )?)/);I=i&&i[1]||""}return`
`+I+t}var Ce=!1;function Xe(t,i){if(!t||Ce)return"";Ce=!0;var a=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{if(i)if(i=function(){throw Error()},Object.defineProperty(i.prototype,"props",{set:function(){throw Error()}}),typeof Reflect=="object"&&Reflect.construct){try{Reflect.construct(i,[])}catch(re){var l=re}Reflect.construct(t,[],i)}else{try{i.call()}catch(re){l=re}t.call(i.prototype)}else{try{throw Error()}catch(re){l=re}t()}}catch(re){if(re&&l&&typeof re.stack=="string"){for(var f=re.stack.split(`
`),h=l.stack.split(`
`),T=f.length-1,N=h.length-1;1<=T&&0<=N&&f[T]!==h[N];)N--;for(;1<=T&&0<=N;T--,N--)if(f[T]!==h[N]){if(T!==1||N!==1)do if(T--,N--,0>N||f[T]!==h[N]){var B=`
`+f[T].replace(" at new "," at ");return t.displayName&&B.includes("<anonymous>")&&(B=B.replace("<anonymous>",t.displayName)),B}while(1<=T&&0<=N);break}}}finally{Ce=!1,Error.prepareStackTrace=a}return(t=t?t.displayName||t.name:"")?j(t):""}function Ze(t){switch(t.tag){case 5:return j(t.type);case 16:return j("Lazy");case 13:return j("Suspense");case 19:return j("SuspenseList");case 0:case 2:case 15:return t=Xe(t.type,!1),t;case 11:return t=Xe(t.type.render,!1),t;case 1:return t=Xe(t.type,!0),t;default:return""}}function ie(t){if(t==null)return null;if(typeof t=="function")return t.displayName||t.name||null;if(typeof t=="string")return t;switch(t){case z:return"Fragment";case U:return"Portal";case D:return"Profiler";case A:return"StrictMode";case Q:return"Suspense";case oe:return"SuspenseList"}if(typeof t=="object")switch(t.$$typeof){case O:return(t.displayName||"Context")+".Consumer";case fe:return(t._context.displayName||"Context")+".Provider";case te:var i=t.render;return t=t.displayName,t||(t=i.displayName||i.name||"",t=t!==""?"ForwardRef("+t+")":"ForwardRef"),t;case K:return i=t.displayName||null,i!==null?i:ie(t.type)||"Memo";case ee:i=t._payload,t=t._init;try{return ie(t(i))}catch{}}return null}function me(t){var i=t.type;switch(t.tag){case 24:return"Cache";case 9:return(i.displayName||"Context")+".Consumer";case 10:return(i._context.displayName||"Context")+".Provider";case 18:return"DehydratedFragment";case 11:return t=i.render,t=t.displayName||t.name||"",i.displayName||(t!==""?"ForwardRef("+t+")":"ForwardRef");case 7:return"Fragment";case 5:return i;case 4:return"Portal";case 3:return"Root";case 6:return"Text";case 16:return ie(i);case 8:return i===A?"StrictMode":"Mode";case 22:return"Offscreen";case 12:return"Profiler";case 21:return"Scope";case 13:return"Suspense";case 19:return"SuspenseList";case 25:return"TracingMarker";case 1:case 0:case 17:case 2:case 14:case 15:if(typeof i=="function")return i.displayName||i.name||null;if(typeof i=="string")return i}return null}function pe(t){switch(typeof t){case"boolean":case"number":case"string":case"undefined":return t;case"object":return t;default:return""}}function Fe(t){var i=t.type;return(t=t.nodeName)&&t.toLowerCase()==="input"&&(i==="checkbox"||i==="radio")}function He(t){var i=Fe(t)?"checked":"value",a=Object.getOwnPropertyDescriptor(t.constructor.prototype,i),l=""+t[i];if(!t.hasOwnProperty(i)&&typeof a<"u"&&typeof a.get=="function"&&typeof a.set=="function"){var f=a.get,h=a.set;return Object.defineProperty(t,i,{configurable:!0,get:function(){return f.call(this)},set:function(T){l=""+T,h.call(this,T)}}),Object.defineProperty(t,i,{enumerable:a.enumerable}),{getValue:function(){return l},setValue:function(T){l=""+T},stopTracking:function(){t._valueTracker=null,delete t[i]}}}}function nt(t){t._valueTracker||(t._valueTracker=He(t))}function Wt(t){if(!t)return!1;var i=t._valueTracker;if(!i)return!0;var a=i.getValue(),l="";return t&&(l=Fe(t)?t.checked?"true":"false":t.value),t=l,t!==a?(i.setValue(t),!0):!1}function ht(t){if(t=t||(typeof document<"u"?document:void 0),typeof t>"u")return null;try{return t.activeElement||t.body}catch{return t.body}}function xt(t,i){var a=i.checked;return le({},i,{defaultChecked:void 0,defaultValue:void 0,value:void 0,checked:a??t._wrapperState.initialChecked})}function Ct(t,i){var a=i.defaultValue==null?"":i.defaultValue,l=i.checked!=null?i.checked:i.defaultChecked;a=pe(i.value!=null?i.value:a),t._wrapperState={initialChecked:l,initialValue:a,controlled:i.type==="checkbox"||i.type==="radio"?i.checked!=null:i.value!=null}}function ut(t,i){i=i.checked,i!=null&&L(t,"checked",i,!1)}function Ft(t,i){ut(t,i);var a=pe(i.value),l=i.type;if(a!=null)l==="number"?(a===0&&t.value===""||t.value!=a)&&(t.value=""+a):t.value!==""+a&&(t.value=""+a);else if(l==="submit"||l==="reset"){t.removeAttribute("value");return}i.hasOwnProperty("value")?kt(t,i.type,a):i.hasOwnProperty("defaultValue")&&kt(t,i.type,pe(i.defaultValue)),i.checked==null&&i.defaultChecked!=null&&(t.defaultChecked=!!i.defaultChecked)}function k(t,i,a){if(i.hasOwnProperty("value")||i.hasOwnProperty("defaultValue")){var l=i.type;if(!(l!=="submit"&&l!=="reset"||i.value!==void 0&&i.value!==null))return;i=""+t._wrapperState.initialValue,a||i===t.value||(t.value=i),t.defaultValue=i}a=t.name,a!==""&&(t.name=""),t.defaultChecked=!!t._wrapperState.initialChecked,a!==""&&(t.name=a)}function kt(t,i,a){(i!=="number"||ht(t.ownerDocument)!==t)&&(a==null?t.defaultValue=""+t._wrapperState.initialValue:t.defaultValue!==""+a&&(t.defaultValue=""+a))}var mt=Array.isArray;function St(t,i,a,l){if(t=t.options,i){i={};for(var f=0;f<a.length;f++)i["$"+a[f]]=!0;for(a=0;a<t.length;a++)f=i.hasOwnProperty("$"+t[a].value),t[a].selected!==f&&(t[a].selected=f),f&&l&&(t[a].defaultSelected=!0)}else{for(a=""+pe(a),i=null,f=0;f<t.length;f++){if(t[f].value===a){t[f].selected=!0,l&&(t[f].defaultSelected=!0);return}i!==null||t[f].disabled||(i=t[f])}i!==null&&(i.selected=!0)}}function Ge(t,i){if(i.dangerouslySetInnerHTML!=null)throw Error(n(91));return le({},i,{value:void 0,defaultValue:void 0,children:""+t._wrapperState.initialValue})}function P(t,i){var a=i.value;if(a==null){if(a=i.children,i=i.defaultValue,a!=null){if(i!=null)throw Error(n(92));if(mt(a)){if(1<a.length)throw Error(n(93));a=a[0]}i=a}i==null&&(i=""),a=i}t._wrapperState={initialValue:pe(a)}}function E(t,i){var a=pe(i.value),l=pe(i.defaultValue);a!=null&&(a=""+a,a!==t.value&&(t.value=a),i.defaultValue==null&&t.defaultValue!==a&&(t.defaultValue=a)),l!=null&&(t.defaultValue=""+l)}function G(t){var i=t.textContent;i===t._wrapperState.initialValue&&i!==""&&i!==null&&(t.value=i)}function de(t){switch(t){case"svg":return"http://www.w3.org/2000/svg";case"math":return"http://www.w3.org/1998/Math/MathML";default:return"http://www.w3.org/1999/xhtml"}}function ge(t,i){return t==null||t==="http://www.w3.org/1999/xhtml"?de(i):t==="http://www.w3.org/2000/svg"&&i==="foreignObject"?"http://www.w3.org/1999/xhtml":t}var ue,Be=(function(t){return typeof MSApp<"u"&&MSApp.execUnsafeLocalFunction?function(i,a,l,f){MSApp.execUnsafeLocalFunction(function(){return t(i,a,l,f)})}:t})(function(t,i){if(t.namespaceURI!=="http://www.w3.org/2000/svg"||"innerHTML"in t)t.innerHTML=i;else{for(ue=ue||document.createElement("div"),ue.innerHTML="<svg>"+i.valueOf().toString()+"</svg>",i=ue.firstChild;t.firstChild;)t.removeChild(t.firstChild);for(;i.firstChild;)t.appendChild(i.firstChild)}});function we(t,i){if(i){var a=t.firstChild;if(a&&a===t.lastChild&&a.nodeType===3){a.nodeValue=i;return}}t.textContent=i}var qe={animationIterationCount:!0,aspectRatio:!0,borderImageOutset:!0,borderImageSlice:!0,borderImageWidth:!0,boxFlex:!0,boxFlexGroup:!0,boxOrdinalGroup:!0,columnCount:!0,columns:!0,flex:!0,flexGrow:!0,flexPositive:!0,flexShrink:!0,flexNegative:!0,flexOrder:!0,gridArea:!0,gridRow:!0,gridRowEnd:!0,gridRowSpan:!0,gridRowStart:!0,gridColumn:!0,gridColumnEnd:!0,gridColumnSpan:!0,gridColumnStart:!0,fontWeight:!0,lineClamp:!0,lineHeight:!0,opacity:!0,order:!0,orphans:!0,tabSize:!0,widows:!0,zIndex:!0,zoom:!0,fillOpacity:!0,floodOpacity:!0,stopOpacity:!0,strokeDasharray:!0,strokeDashoffset:!0,strokeMiterlimit:!0,strokeOpacity:!0,strokeWidth:!0},it=["Webkit","ms","Moz","O"];Object.keys(qe).forEach(function(t){it.forEach(function(i){i=i+t.charAt(0).toUpperCase()+t.substring(1),qe[i]=qe[t]})});function Se(t,i,a){return i==null||typeof i=="boolean"||i===""?"":a||typeof i!="number"||i===0||qe.hasOwnProperty(t)&&qe[t]?(""+i).trim():i+"px"}function Te(t,i){t=t.style;for(var a in i)if(i.hasOwnProperty(a)){var l=a.indexOf("--")===0,f=Se(a,i[a],l);a==="float"&&(a="cssFloat"),l?t.setProperty(a,f):t[a]=f}}var We=le({menuitem:!0},{area:!0,base:!0,br:!0,col:!0,embed:!0,hr:!0,img:!0,input:!0,keygen:!0,link:!0,meta:!0,param:!0,source:!0,track:!0,wbr:!0});function ke(t,i){if(i){if(We[t]&&(i.children!=null||i.dangerouslySetInnerHTML!=null))throw Error(n(137,t));if(i.dangerouslySetInnerHTML!=null){if(i.children!=null)throw Error(n(60));if(typeof i.dangerouslySetInnerHTML!="object"||!("__html"in i.dangerouslySetInnerHTML))throw Error(n(61))}if(i.style!=null&&typeof i.style!="object")throw Error(n(62))}}function De(t,i){if(t.indexOf("-")===-1)return typeof i.is=="string";switch(t){case"annotation-xml":case"color-profile":case"font-face":case"font-face-src":case"font-face-uri":case"font-face-format":case"font-face-name":case"missing-glyph":return!1;default:return!0}}var lt=null;function V(t){return t=t.target||t.srcElement||window,t.correspondingUseElement&&(t=t.correspondingUseElement),t.nodeType===3?t.parentNode:t}var Ae=null,Me=null,Le=null;function ye(t){if(t=pa(t)){if(typeof Ae!="function")throw Error(n(280));var i=t.stateNode;i&&(i=go(i),Ae(t.stateNode,t.type,i))}}function ce(t){Me?Le?Le.push(t):Le=[t]:Me=t}function ze(){if(Me){var t=Me,i=Le;if(Le=Me=null,ye(t),i)for(t=0;t<i.length;t++)ye(i[t])}}function rt(t,i){return t(i)}function Pt(){}var yt=!1;function Wn(t,i,a){if(yt)return t(i,a);yt=!0;try{return rt(t,i,a)}finally{yt=!1,(Me!==null||Le!==null)&&(Pt(),ze())}}function vn(t,i){var a=t.stateNode;if(a===null)return null;var l=go(a);if(l===null)return null;a=l[i];e:switch(i){case"onClick":case"onClickCapture":case"onDoubleClick":case"onDoubleClickCapture":case"onMouseDown":case"onMouseDownCapture":case"onMouseMove":case"onMouseMoveCapture":case"onMouseUp":case"onMouseUpCapture":case"onMouseEnter":(l=!l.disabled)||(t=t.type,l=!(t==="button"||t==="input"||t==="select"||t==="textarea")),t=!l;break e;default:t=!1}if(t)return null;if(a&&typeof a!="function")throw Error(n(231,i,typeof a));return a}var ns=!1;if(d)try{var Li={};Object.defineProperty(Li,"passive",{get:function(){ns=!0}}),window.addEventListener("test",Li,Li),window.removeEventListener("test",Li,Li)}catch{ns=!1}function Gl(t,i,a,l,f,h,T,N,B){var re=Array.prototype.slice.call(arguments,3);try{i.apply(a,re)}catch(ve){this.onError(ve)}}var Ji=!1,br=null,Xn=!1,Pr=null,Ya={onError:function(t){Ji=!0,br=t}};function qa(t,i,a,l,f,h,T,N,B){Ji=!1,br=null,Gl.apply(Ya,arguments)}function is(t,i,a,l,f,h,T,N,B){if(qa.apply(this,arguments),Ji){if(Ji){var re=br;Ji=!1,br=null}else throw Error(n(198));Xn||(Xn=!0,Pr=re)}}function _i(t){var i=t,a=t;if(t.alternate)for(;i.return;)i=i.return;else{t=i;do i=t,(i.flags&4098)!==0&&(a=i.return),t=i.return;while(t)}return i.tag===3?a:null}function Dr(t){if(t.tag===13){var i=t.memoizedState;if(i===null&&(t=t.alternate,t!==null&&(i=t.memoizedState)),i!==null)return i.dehydrated}return null}function Ks(t){if(_i(t)!==t)throw Error(n(188))}function $a(t){var i=t.alternate;if(!i){if(i=_i(t),i===null)throw Error(n(188));return i!==t?null:t}for(var a=t,l=i;;){var f=a.return;if(f===null)break;var h=f.alternate;if(h===null){if(l=f.return,l!==null){a=l;continue}break}if(f.child===h.child){for(h=f.child;h;){if(h===a)return Ks(f),t;if(h===l)return Ks(f),i;h=h.sibling}throw Error(n(188))}if(a.return!==l.return)a=f,l=h;else{for(var T=!1,N=f.child;N;){if(N===a){T=!0,a=f,l=h;break}if(N===l){T=!0,l=f,a=h;break}N=N.sibling}if(!T){for(N=h.child;N;){if(N===a){T=!0,a=h,l=f;break}if(N===l){T=!0,l=h,a=f;break}N=N.sibling}if(!T)throw Error(n(189))}}if(a.alternate!==l)throw Error(n(190))}if(a.tag!==3)throw Error(n(188));return a.stateNode.current===a?t:i}function Ka(t){return t=$a(t),t!==null?Za(t):null}function Za(t){if(t.tag===5||t.tag===6)return t;for(t=t.child;t!==null;){var i=Za(t);if(i!==null)return i;t=t.sibling}return null}var Qa=e.unstable_scheduleCallback,Ja=e.unstable_cancelCallback,Wl=e.unstable_shouldYield,Xl=e.unstable_requestPaint,w=e.unstable_now,X=e.unstable_getCurrentPriorityLevel,se=e.unstable_ImmediatePriority,J=e.unstable_UserBlockingPriority,$=e.unstable_NormalPriority,be=e.unstable_LowPriority,Ue=e.unstable_IdlePriority,Re=null,Ne=null;function Ke(t){if(Ne&&typeof Ne.onCommitFiberRoot=="function")try{Ne.onCommitFiberRoot(Re,t,void 0,(t.current.flags&128)===128)}catch{}}var Je=Math.clz32?Math.clz32:Rt,ct=Math.log,Qe=Math.LN2;function Rt(t){return t>>>=0,t===0?32:31-(ct(t)/Qe|0)|0}var It=64,Nt=4194304;function vt(t){switch(t&-t){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return t&4194240;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return t&130023424;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 1073741824;default:return t}}function Xt(t,i){var a=t.pendingLanes;if(a===0)return 0;var l=0,f=t.suspendedLanes,h=t.pingedLanes,T=a&268435455;if(T!==0){var N=T&~f;N!==0?l=vt(N):(h&=T,h!==0&&(l=vt(h)))}else T=a&~f,T!==0?l=vt(T):h!==0&&(l=vt(h));if(l===0)return 0;if(i!==0&&i!==l&&(i&f)===0&&(f=l&-l,h=i&-i,f>=h||f===16&&(h&4194240)!==0))return i;if((l&4)!==0&&(l|=a&16),i=t.entangledLanes,i!==0)for(t=t.entanglements,i&=l;0<i;)a=31-Je(i),f=1<<a,l|=t[a],i&=~f;return l}function Ye(t,i){switch(t){case 1:case 2:case 4:return i+250;case 8:case 16:case 32:case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return i+5e3;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return-1;case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function xn(t,i){for(var a=t.suspendedLanes,l=t.pingedLanes,f=t.expirationTimes,h=t.pendingLanes;0<h;){var T=31-Je(h),N=1<<T,B=f[T];B===-1?((N&a)===0||(N&l)!==0)&&(f[T]=Ye(N,i)):B<=i&&(t.expiredLanes|=N),h&=~N}}function gt(t){return t=t.pendingLanes&-1073741825,t!==0?t:t&1073741824?1073741824:0}function wn(){var t=It;return It<<=1,(It&4194240)===0&&(It=64),t}function An(t){for(var i=[],a=0;31>a;a++)i.push(t);return i}function Fn(t,i,a){t.pendingLanes|=i,i!==536870912&&(t.suspendedLanes=0,t.pingedLanes=0),t=t.eventTimes,i=31-Je(i),t[i]=a}function er(t,i){var a=t.pendingLanes&~i;t.pendingLanes=i,t.suspendedLanes=0,t.pingedLanes=0,t.expiredLanes&=i,t.mutableReadLanes&=i,t.entangledLanes&=i,i=t.entanglements;var l=t.eventTimes;for(t=t.expirationTimes;0<a;){var f=31-Je(a),h=1<<f;i[f]=0,l[f]=-1,t[f]=-1,a&=~h}}function At(t,i){var a=t.entangledLanes|=i;for(t=t.entanglements;a;){var l=31-Je(a),f=1<<l;f&i|t[l]&i&&(t[l]|=i),a&=~f}}var st=0;function ri(t){return t&=-t,1<t?4<t?(t&268435455)!==0?16:536870912:4:1}var jt,jn,Ni,Zs,fd,jl=!1,eo=[],tr=null,nr=null,ir=null,Qs=new Map,Js=new Map,rr=[],vg="mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");function dd(t,i){switch(t){case"focusin":case"focusout":tr=null;break;case"dragenter":case"dragleave":nr=null;break;case"mouseover":case"mouseout":ir=null;break;case"pointerover":case"pointerout":Qs.delete(i.pointerId);break;case"gotpointercapture":case"lostpointercapture":Js.delete(i.pointerId)}}function ea(t,i,a,l,f,h){return t===null||t.nativeEvent!==h?(t={blockedOn:i,domEventName:a,eventSystemFlags:l,nativeEvent:h,targetContainers:[f]},i!==null&&(i=pa(i),i!==null&&jn(i)),t):(t.eventSystemFlags|=l,i=t.targetContainers,f!==null&&i.indexOf(f)===-1&&i.push(f),t)}function xg(t,i,a,l,f){switch(i){case"focusin":return tr=ea(tr,t,i,a,l,f),!0;case"dragenter":return nr=ea(nr,t,i,a,l,f),!0;case"mouseover":return ir=ea(ir,t,i,a,l,f),!0;case"pointerover":var h=f.pointerId;return Qs.set(h,ea(Qs.get(h)||null,t,i,a,l,f)),!0;case"gotpointercapture":return h=f.pointerId,Js.set(h,ea(Js.get(h)||null,t,i,a,l,f)),!0}return!1}function hd(t){var i=Lr(t.target);if(i!==null){var a=_i(i);if(a!==null){if(i=a.tag,i===13){if(i=Dr(a),i!==null){t.blockedOn=i,fd(t.priority,function(){Ni(a)});return}}else if(i===3&&a.stateNode.current.memoizedState.isDehydrated){t.blockedOn=a.tag===3?a.stateNode.containerInfo:null;return}}}t.blockedOn=null}function to(t){if(t.blockedOn!==null)return!1;for(var i=t.targetContainers;0<i.length;){var a=ql(t.domEventName,t.eventSystemFlags,i[0],t.nativeEvent);if(a===null){a=t.nativeEvent;var l=new a.constructor(a.type,a);lt=l,a.target.dispatchEvent(l),lt=null}else return i=pa(a),i!==null&&jn(i),t.blockedOn=a,!1;i.shift()}return!0}function pd(t,i,a){to(t)&&a.delete(i)}function Sg(){jl=!1,tr!==null&&to(tr)&&(tr=null),nr!==null&&to(nr)&&(nr=null),ir!==null&&to(ir)&&(ir=null),Qs.forEach(pd),Js.forEach(pd)}function ta(t,i){t.blockedOn===i&&(t.blockedOn=null,jl||(jl=!0,e.unstable_scheduleCallback(e.unstable_NormalPriority,Sg)))}function na(t){function i(f){return ta(f,t)}if(0<eo.length){ta(eo[0],t);for(var a=1;a<eo.length;a++){var l=eo[a];l.blockedOn===t&&(l.blockedOn=null)}}for(tr!==null&&ta(tr,t),nr!==null&&ta(nr,t),ir!==null&&ta(ir,t),Qs.forEach(i),Js.forEach(i),a=0;a<rr.length;a++)l=rr[a],l.blockedOn===t&&(l.blockedOn=null);for(;0<rr.length&&(a=rr[0],a.blockedOn===null);)hd(a),a.blockedOn===null&&rr.shift()}var rs=b.ReactCurrentBatchConfig,no=!0;function yg(t,i,a,l){var f=st,h=rs.transition;rs.transition=null;try{st=1,Yl(t,i,a,l)}finally{st=f,rs.transition=h}}function Mg(t,i,a,l){var f=st,h=rs.transition;rs.transition=null;try{st=4,Yl(t,i,a,l)}finally{st=f,rs.transition=h}}function Yl(t,i,a,l){if(no){var f=ql(t,i,a,l);if(f===null)fu(t,i,l,io,a),dd(t,l);else if(xg(f,t,i,a,l))l.stopPropagation();else if(dd(t,l),i&4&&-1<vg.indexOf(t)){for(;f!==null;){var h=pa(f);if(h!==null&&jt(h),h=ql(t,i,a,l),h===null&&fu(t,i,l,io,a),h===f)break;f=h}f!==null&&l.stopPropagation()}else fu(t,i,l,null,a)}}var io=null;function ql(t,i,a,l){if(io=null,t=V(l),t=Lr(t),t!==null)if(i=_i(t),i===null)t=null;else if(a=i.tag,a===13){if(t=Dr(i),t!==null)return t;t=null}else if(a===3){if(i.stateNode.current.memoizedState.isDehydrated)return i.tag===3?i.stateNode.containerInfo:null;t=null}else i!==t&&(t=null);return io=t,null}function md(t){switch(t){case"cancel":case"click":case"close":case"contextmenu":case"copy":case"cut":case"auxclick":case"dblclick":case"dragend":case"dragstart":case"drop":case"focusin":case"focusout":case"input":case"invalid":case"keydown":case"keypress":case"keyup":case"mousedown":case"mouseup":case"paste":case"pause":case"play":case"pointercancel":case"pointerdown":case"pointerup":case"ratechange":case"reset":case"resize":case"seeked":case"submit":case"touchcancel":case"touchend":case"touchstart":case"volumechange":case"change":case"selectionchange":case"textInput":case"compositionstart":case"compositionend":case"compositionupdate":case"beforeblur":case"afterblur":case"beforeinput":case"blur":case"fullscreenchange":case"focus":case"hashchange":case"popstate":case"select":case"selectstart":return 1;case"drag":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"mousemove":case"mouseout":case"mouseover":case"pointermove":case"pointerout":case"pointerover":case"scroll":case"toggle":case"touchmove":case"wheel":case"mouseenter":case"mouseleave":case"pointerenter":case"pointerleave":return 4;case"message":switch(X()){case se:return 1;case J:return 4;case $:case be:return 16;case Ue:return 536870912;default:return 16}default:return 16}}var sr=null,$l=null,ro=null;function gd(){if(ro)return ro;var t,i=$l,a=i.length,l,f="value"in sr?sr.value:sr.textContent,h=f.length;for(t=0;t<a&&i[t]===f[t];t++);var T=a-t;for(l=1;l<=T&&i[a-l]===f[h-l];l++);return ro=f.slice(t,1<l?1-l:void 0)}function so(t){var i=t.keyCode;return"charCode"in t?(t=t.charCode,t===0&&i===13&&(t=13)):t=i,t===10&&(t=13),32<=t||t===13?t:0}function ao(){return!0}function _d(){return!1}function On(t){function i(a,l,f,h,T){this._reactName=a,this._targetInst=f,this.type=l,this.nativeEvent=h,this.target=T,this.currentTarget=null;for(var N in t)t.hasOwnProperty(N)&&(a=t[N],this[N]=a?a(h):h[N]);return this.isDefaultPrevented=(h.defaultPrevented!=null?h.defaultPrevented:h.returnValue===!1)?ao:_d,this.isPropagationStopped=_d,this}return le(i.prototype,{preventDefault:function(){this.defaultPrevented=!0;var a=this.nativeEvent;a&&(a.preventDefault?a.preventDefault():typeof a.returnValue!="unknown"&&(a.returnValue=!1),this.isDefaultPrevented=ao)},stopPropagation:function(){var a=this.nativeEvent;a&&(a.stopPropagation?a.stopPropagation():typeof a.cancelBubble!="unknown"&&(a.cancelBubble=!0),this.isPropagationStopped=ao)},persist:function(){},isPersistent:ao}),i}var ss={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(t){return t.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},Kl=On(ss),ia=le({},ss,{view:0,detail:0}),Eg=On(ia),Zl,Ql,ra,oo=le({},ia,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:eu,button:0,buttons:0,relatedTarget:function(t){return t.relatedTarget===void 0?t.fromElement===t.srcElement?t.toElement:t.fromElement:t.relatedTarget},movementX:function(t){return"movementX"in t?t.movementX:(t!==ra&&(ra&&t.type==="mousemove"?(Zl=t.screenX-ra.screenX,Ql=t.screenY-ra.screenY):Ql=Zl=0,ra=t),Zl)},movementY:function(t){return"movementY"in t?t.movementY:Ql}}),vd=On(oo),Tg=le({},oo,{dataTransfer:0}),wg=On(Tg),Ag=le({},ia,{relatedTarget:0}),Jl=On(Ag),Cg=le({},ss,{animationName:0,elapsedTime:0,pseudoElement:0}),Rg=On(Cg),bg=le({},ss,{clipboardData:function(t){return"clipboardData"in t?t.clipboardData:window.clipboardData}}),Pg=On(bg),Dg=le({},ss,{data:0}),xd=On(Dg),Lg={Esc:"Escape",Spacebar:" ",Left:"ArrowLeft",Up:"ArrowUp",Right:"ArrowRight",Down:"ArrowDown",Del:"Delete",Win:"OS",Menu:"ContextMenu",Apps:"ContextMenu",Scroll:"ScrollLock",MozPrintableKey:"Unidentified"},Ng={8:"Backspace",9:"Tab",12:"Clear",13:"Enter",16:"Shift",17:"Control",18:"Alt",19:"Pause",20:"CapsLock",27:"Escape",32:" ",33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"ArrowLeft",38:"ArrowUp",39:"ArrowRight",40:"ArrowDown",45:"Insert",46:"Delete",112:"F1",113:"F2",114:"F3",115:"F4",116:"F5",117:"F6",118:"F7",119:"F8",120:"F9",121:"F10",122:"F11",123:"F12",144:"NumLock",145:"ScrollLock",224:"Meta"},Ig={Alt:"altKey",Control:"ctrlKey",Meta:"metaKey",Shift:"shiftKey"};function Ug(t){var i=this.nativeEvent;return i.getModifierState?i.getModifierState(t):(t=Ig[t])?!!i[t]:!1}function eu(){return Ug}var Fg=le({},ia,{key:function(t){if(t.key){var i=Lg[t.key]||t.key;if(i!=="Unidentified")return i}return t.type==="keypress"?(t=so(t),t===13?"Enter":String.fromCharCode(t)):t.type==="keydown"||t.type==="keyup"?Ng[t.keyCode]||"Unidentified":""},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:eu,charCode:function(t){return t.type==="keypress"?so(t):0},keyCode:function(t){return t.type==="keydown"||t.type==="keyup"?t.keyCode:0},which:function(t){return t.type==="keypress"?so(t):t.type==="keydown"||t.type==="keyup"?t.keyCode:0}}),Og=On(Fg),Bg=le({},oo,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0}),Sd=On(Bg),kg=le({},ia,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:eu}),zg=On(kg),Vg=le({},ss,{propertyName:0,elapsedTime:0,pseudoElement:0}),Hg=On(Vg),Gg=le({},oo,{deltaX:function(t){return"deltaX"in t?t.deltaX:"wheelDeltaX"in t?-t.wheelDeltaX:0},deltaY:function(t){return"deltaY"in t?t.deltaY:"wheelDeltaY"in t?-t.wheelDeltaY:"wheelDelta"in t?-t.wheelDelta:0},deltaZ:0,deltaMode:0}),Wg=On(Gg),Xg=[9,13,27,32],tu=d&&"CompositionEvent"in window,sa=null;d&&"documentMode"in document&&(sa=document.documentMode);var jg=d&&"TextEvent"in window&&!sa,yd=d&&(!tu||sa&&8<sa&&11>=sa),Md=" ",Ed=!1;function Td(t,i){switch(t){case"keyup":return Xg.indexOf(i.keyCode)!==-1;case"keydown":return i.keyCode!==229;case"keypress":case"mousedown":case"focusout":return!0;default:return!1}}function wd(t){return t=t.detail,typeof t=="object"&&"data"in t?t.data:null}var as=!1;function Yg(t,i){switch(t){case"compositionend":return wd(i);case"keypress":return i.which!==32?null:(Ed=!0,Md);case"textInput":return t=i.data,t===Md&&Ed?null:t;default:return null}}function qg(t,i){if(as)return t==="compositionend"||!tu&&Td(t,i)?(t=gd(),ro=$l=sr=null,as=!1,t):null;switch(t){case"paste":return null;case"keypress":if(!(i.ctrlKey||i.altKey||i.metaKey)||i.ctrlKey&&i.altKey){if(i.char&&1<i.char.length)return i.char;if(i.which)return String.fromCharCode(i.which)}return null;case"compositionend":return yd&&i.locale!=="ko"?null:i.data;default:return null}}var $g={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function Ad(t){var i=t&&t.nodeName&&t.nodeName.toLowerCase();return i==="input"?!!$g[t.type]:i==="textarea"}function Cd(t,i,a,l){ce(l),i=ho(i,"onChange"),0<i.length&&(a=new Kl("onChange","change",null,a,l),t.push({event:a,listeners:i}))}var aa=null,oa=null;function Kg(t){Xd(t,0)}function lo(t){var i=fs(t);if(Wt(i))return t}function Zg(t,i){if(t==="change")return i}var Rd=!1;if(d){var nu;if(d){var iu="oninput"in document;if(!iu){var bd=document.createElement("div");bd.setAttribute("oninput","return;"),iu=typeof bd.oninput=="function"}nu=iu}else nu=!1;Rd=nu&&(!document.documentMode||9<document.documentMode)}function Pd(){aa&&(aa.detachEvent("onpropertychange",Dd),oa=aa=null)}function Dd(t){if(t.propertyName==="value"&&lo(oa)){var i=[];Cd(i,oa,t,V(t)),Wn(Kg,i)}}function Qg(t,i,a){t==="focusin"?(Pd(),aa=i,oa=a,aa.attachEvent("onpropertychange",Dd)):t==="focusout"&&Pd()}function Jg(t){if(t==="selectionchange"||t==="keyup"||t==="keydown")return lo(oa)}function e_(t,i){if(t==="click")return lo(i)}function t_(t,i){if(t==="input"||t==="change")return lo(i)}function n_(t,i){return t===i&&(t!==0||1/t===1/i)||t!==t&&i!==i}var si=typeof Object.is=="function"?Object.is:n_;function la(t,i){if(si(t,i))return!0;if(typeof t!="object"||t===null||typeof i!="object"||i===null)return!1;var a=Object.keys(t),l=Object.keys(i);if(a.length!==l.length)return!1;for(l=0;l<a.length;l++){var f=a[l];if(!p.call(i,f)||!si(t[f],i[f]))return!1}return!0}function Ld(t){for(;t&&t.firstChild;)t=t.firstChild;return t}function Nd(t,i){var a=Ld(t);t=0;for(var l;a;){if(a.nodeType===3){if(l=t+a.textContent.length,t<=i&&l>=i)return{node:a,offset:i-t};t=l}e:{for(;a;){if(a.nextSibling){a=a.nextSibling;break e}a=a.parentNode}a=void 0}a=Ld(a)}}function Id(t,i){return t&&i?t===i?!0:t&&t.nodeType===3?!1:i&&i.nodeType===3?Id(t,i.parentNode):"contains"in t?t.contains(i):t.compareDocumentPosition?!!(t.compareDocumentPosition(i)&16):!1:!1}function Ud(){for(var t=window,i=ht();i instanceof t.HTMLIFrameElement;){try{var a=typeof i.contentWindow.location.href=="string"}catch{a=!1}if(a)t=i.contentWindow;else break;i=ht(t.document)}return i}function ru(t){var i=t&&t.nodeName&&t.nodeName.toLowerCase();return i&&(i==="input"&&(t.type==="text"||t.type==="search"||t.type==="tel"||t.type==="url"||t.type==="password")||i==="textarea"||t.contentEditable==="true")}function i_(t){var i=Ud(),a=t.focusedElem,l=t.selectionRange;if(i!==a&&a&&a.ownerDocument&&Id(a.ownerDocument.documentElement,a)){if(l!==null&&ru(a)){if(i=l.start,t=l.end,t===void 0&&(t=i),"selectionStart"in a)a.selectionStart=i,a.selectionEnd=Math.min(t,a.value.length);else if(t=(i=a.ownerDocument||document)&&i.defaultView||window,t.getSelection){t=t.getSelection();var f=a.textContent.length,h=Math.min(l.start,f);l=l.end===void 0?h:Math.min(l.end,f),!t.extend&&h>l&&(f=l,l=h,h=f),f=Nd(a,h);var T=Nd(a,l);f&&T&&(t.rangeCount!==1||t.anchorNode!==f.node||t.anchorOffset!==f.offset||t.focusNode!==T.node||t.focusOffset!==T.offset)&&(i=i.createRange(),i.setStart(f.node,f.offset),t.removeAllRanges(),h>l?(t.addRange(i),t.extend(T.node,T.offset)):(i.setEnd(T.node,T.offset),t.addRange(i)))}}for(i=[],t=a;t=t.parentNode;)t.nodeType===1&&i.push({element:t,left:t.scrollLeft,top:t.scrollTop});for(typeof a.focus=="function"&&a.focus(),a=0;a<i.length;a++)t=i[a],t.element.scrollLeft=t.left,t.element.scrollTop=t.top}}var r_=d&&"documentMode"in document&&11>=document.documentMode,os=null,su=null,ua=null,au=!1;function Fd(t,i,a){var l=a.window===a?a.document:a.nodeType===9?a:a.ownerDocument;au||os==null||os!==ht(l)||(l=os,"selectionStart"in l&&ru(l)?l={start:l.selectionStart,end:l.selectionEnd}:(l=(l.ownerDocument&&l.ownerDocument.defaultView||window).getSelection(),l={anchorNode:l.anchorNode,anchorOffset:l.anchorOffset,focusNode:l.focusNode,focusOffset:l.focusOffset}),ua&&la(ua,l)||(ua=l,l=ho(su,"onSelect"),0<l.length&&(i=new Kl("onSelect","select",null,i,a),t.push({event:i,listeners:l}),i.target=os)))}function uo(t,i){var a={};return a[t.toLowerCase()]=i.toLowerCase(),a["Webkit"+t]="webkit"+i,a["Moz"+t]="moz"+i,a}var ls={animationend:uo("Animation","AnimationEnd"),animationiteration:uo("Animation","AnimationIteration"),animationstart:uo("Animation","AnimationStart"),transitionend:uo("Transition","TransitionEnd")},ou={},Od={};d&&(Od=document.createElement("div").style,"AnimationEvent"in window||(delete ls.animationend.animation,delete ls.animationiteration.animation,delete ls.animationstart.animation),"TransitionEvent"in window||delete ls.transitionend.transition);function co(t){if(ou[t])return ou[t];if(!ls[t])return t;var i=ls[t],a;for(a in i)if(i.hasOwnProperty(a)&&a in Od)return ou[t]=i[a];return t}var Bd=co("animationend"),kd=co("animationiteration"),zd=co("animationstart"),Vd=co("transitionend"),Hd=new Map,Gd="abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");function ar(t,i){Hd.set(t,i),u(i,[t])}for(var lu=0;lu<Gd.length;lu++){var uu=Gd[lu],s_=uu.toLowerCase(),a_=uu[0].toUpperCase()+uu.slice(1);ar(s_,"on"+a_)}ar(Bd,"onAnimationEnd"),ar(kd,"onAnimationIteration"),ar(zd,"onAnimationStart"),ar("dblclick","onDoubleClick"),ar("focusin","onFocus"),ar("focusout","onBlur"),ar(Vd,"onTransitionEnd"),c("onMouseEnter",["mouseout","mouseover"]),c("onMouseLeave",["mouseout","mouseover"]),c("onPointerEnter",["pointerout","pointerover"]),c("onPointerLeave",["pointerout","pointerover"]),u("onChange","change click focusin focusout input keydown keyup selectionchange".split(" ")),u("onSelect","focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")),u("onBeforeInput",["compositionend","keypress","textInput","paste"]),u("onCompositionEnd","compositionend focusout keydown keypress keyup mousedown".split(" ")),u("onCompositionStart","compositionstart focusout keydown keypress keyup mousedown".split(" ")),u("onCompositionUpdate","compositionupdate focusout keydown keypress keyup mousedown".split(" "));var ca="abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "),o_=new Set("cancel close invalid load scroll toggle".split(" ").concat(ca));function Wd(t,i,a){var l=t.type||"unknown-event";t.currentTarget=a,is(l,i,void 0,t),t.currentTarget=null}function Xd(t,i){i=(i&4)!==0;for(var a=0;a<t.length;a++){var l=t[a],f=l.event;l=l.listeners;e:{var h=void 0;if(i)for(var T=l.length-1;0<=T;T--){var N=l[T],B=N.instance,re=N.currentTarget;if(N=N.listener,B!==h&&f.isPropagationStopped())break e;Wd(f,N,re),h=B}else for(T=0;T<l.length;T++){if(N=l[T],B=N.instance,re=N.currentTarget,N=N.listener,B!==h&&f.isPropagationStopped())break e;Wd(f,N,re),h=B}}}if(Xn)throw t=Pr,Xn=!1,Pr=null,t}function Ot(t,i){var a=i[_u];a===void 0&&(a=i[_u]=new Set);var l=t+"__bubble";a.has(l)||(jd(i,t,2,!1),a.add(l))}function cu(t,i,a){var l=0;i&&(l|=4),jd(a,t,l,i)}var fo="_reactListening"+Math.random().toString(36).slice(2);function fa(t){if(!t[fo]){t[fo]=!0,r.forEach(function(a){a!=="selectionchange"&&(o_.has(a)||cu(a,!1,t),cu(a,!0,t))});var i=t.nodeType===9?t:t.ownerDocument;i===null||i[fo]||(i[fo]=!0,cu("selectionchange",!1,i))}}function jd(t,i,a,l){switch(md(i)){case 1:var f=yg;break;case 4:f=Mg;break;default:f=Yl}a=f.bind(null,i,a,t),f=void 0,!ns||i!=="touchstart"&&i!=="touchmove"&&i!=="wheel"||(f=!0),l?f!==void 0?t.addEventListener(i,a,{capture:!0,passive:f}):t.addEventListener(i,a,!0):f!==void 0?t.addEventListener(i,a,{passive:f}):t.addEventListener(i,a,!1)}function fu(t,i,a,l,f){var h=l;if((i&1)===0&&(i&2)===0&&l!==null)e:for(;;){if(l===null)return;var T=l.tag;if(T===3||T===4){var N=l.stateNode.containerInfo;if(N===f||N.nodeType===8&&N.parentNode===f)break;if(T===4)for(T=l.return;T!==null;){var B=T.tag;if((B===3||B===4)&&(B=T.stateNode.containerInfo,B===f||B.nodeType===8&&B.parentNode===f))return;T=T.return}for(;N!==null;){if(T=Lr(N),T===null)return;if(B=T.tag,B===5||B===6){l=h=T;continue e}N=N.parentNode}}l=l.return}Wn(function(){var re=h,ve=V(a),xe=[];e:{var _e=Hd.get(t);if(_e!==void 0){var Ie=Kl,Ve=t;switch(t){case"keypress":if(so(a)===0)break e;case"keydown":case"keyup":Ie=Og;break;case"focusin":Ve="focus",Ie=Jl;break;case"focusout":Ve="blur",Ie=Jl;break;case"beforeblur":case"afterblur":Ie=Jl;break;case"click":if(a.button===2)break e;case"auxclick":case"dblclick":case"mousedown":case"mousemove":case"mouseup":case"mouseout":case"mouseover":case"contextmenu":Ie=vd;break;case"drag":case"dragend":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"dragstart":case"drop":Ie=wg;break;case"touchcancel":case"touchend":case"touchmove":case"touchstart":Ie=zg;break;case Bd:case kd:case zd:Ie=Rg;break;case Vd:Ie=Hg;break;case"scroll":Ie=Eg;break;case"wheel":Ie=Wg;break;case"copy":case"cut":case"paste":Ie=Pg;break;case"gotpointercapture":case"lostpointercapture":case"pointercancel":case"pointerdown":case"pointermove":case"pointerout":case"pointerover":case"pointerup":Ie=Sd}var je=(i&4)!==0,Yt=!je&&t==="scroll",Y=je?_e!==null?_e+"Capture":null:_e;je=[];for(var H=re,Z;H!==null;){Z=H;var Ee=Z.stateNode;if(Z.tag===5&&Ee!==null&&(Z=Ee,Y!==null&&(Ee=vn(H,Y),Ee!=null&&je.push(da(H,Ee,Z)))),Yt)break;H=H.return}0<je.length&&(_e=new Ie(_e,Ve,null,a,ve),xe.push({event:_e,listeners:je}))}}if((i&7)===0){e:{if(_e=t==="mouseover"||t==="pointerover",Ie=t==="mouseout"||t==="pointerout",_e&&a!==lt&&(Ve=a.relatedTarget||a.fromElement)&&(Lr(Ve)||Ve[Ii]))break e;if((Ie||_e)&&(_e=ve.window===ve?ve:(_e=ve.ownerDocument)?_e.defaultView||_e.parentWindow:window,Ie?(Ve=a.relatedTarget||a.toElement,Ie=re,Ve=Ve?Lr(Ve):null,Ve!==null&&(Yt=_i(Ve),Ve!==Yt||Ve.tag!==5&&Ve.tag!==6)&&(Ve=null)):(Ie=null,Ve=re),Ie!==Ve)){if(je=vd,Ee="onMouseLeave",Y="onMouseEnter",H="mouse",(t==="pointerout"||t==="pointerover")&&(je=Sd,Ee="onPointerLeave",Y="onPointerEnter",H="pointer"),Yt=Ie==null?_e:fs(Ie),Z=Ve==null?_e:fs(Ve),_e=new je(Ee,H+"leave",Ie,a,ve),_e.target=Yt,_e.relatedTarget=Z,Ee=null,Lr(ve)===re&&(je=new je(Y,H+"enter",Ve,a,ve),je.target=Z,je.relatedTarget=Yt,Ee=je),Yt=Ee,Ie&&Ve)t:{for(je=Ie,Y=Ve,H=0,Z=je;Z;Z=us(Z))H++;for(Z=0,Ee=Y;Ee;Ee=us(Ee))Z++;for(;0<H-Z;)je=us(je),H--;for(;0<Z-H;)Y=us(Y),Z--;for(;H--;){if(je===Y||Y!==null&&je===Y.alternate)break t;je=us(je),Y=us(Y)}je=null}else je=null;Ie!==null&&Yd(xe,_e,Ie,je,!1),Ve!==null&&Yt!==null&&Yd(xe,Yt,Ve,je,!0)}}e:{if(_e=re?fs(re):window,Ie=_e.nodeName&&_e.nodeName.toLowerCase(),Ie==="select"||Ie==="input"&&_e.type==="file")var $e=Zg;else if(Ad(_e))if(Rd)$e=t_;else{$e=Jg;var et=Qg}else(Ie=_e.nodeName)&&Ie.toLowerCase()==="input"&&(_e.type==="checkbox"||_e.type==="radio")&&($e=e_);if($e&&($e=$e(t,re))){Cd(xe,$e,a,ve);break e}et&&et(t,_e,re),t==="focusout"&&(et=_e._wrapperState)&&et.controlled&&_e.type==="number"&&kt(_e,"number",_e.value)}switch(et=re?fs(re):window,t){case"focusin":(Ad(et)||et.contentEditable==="true")&&(os=et,su=re,ua=null);break;case"focusout":ua=su=os=null;break;case"mousedown":au=!0;break;case"contextmenu":case"mouseup":case"dragend":au=!1,Fd(xe,a,ve);break;case"selectionchange":if(r_)break;case"keydown":case"keyup":Fd(xe,a,ve)}var tt;if(tu)e:{switch(t){case"compositionstart":var at="onCompositionStart";break e;case"compositionend":at="onCompositionEnd";break e;case"compositionupdate":at="onCompositionUpdate";break e}at=void 0}else as?Td(t,a)&&(at="onCompositionEnd"):t==="keydown"&&a.keyCode===229&&(at="onCompositionStart");at&&(yd&&a.locale!=="ko"&&(as||at!=="onCompositionStart"?at==="onCompositionEnd"&&as&&(tt=gd()):(sr=ve,$l="value"in sr?sr.value:sr.textContent,as=!0)),et=ho(re,at),0<et.length&&(at=new xd(at,t,null,a,ve),xe.push({event:at,listeners:et}),tt?at.data=tt:(tt=wd(a),tt!==null&&(at.data=tt)))),(tt=jg?Yg(t,a):qg(t,a))&&(re=ho(re,"onBeforeInput"),0<re.length&&(ve=new xd("onBeforeInput","beforeinput",null,a,ve),xe.push({event:ve,listeners:re}),ve.data=tt))}Xd(xe,i)})}function da(t,i,a){return{instance:t,listener:i,currentTarget:a}}function ho(t,i){for(var a=i+"Capture",l=[];t!==null;){var f=t,h=f.stateNode;f.tag===5&&h!==null&&(f=h,h=vn(t,a),h!=null&&l.unshift(da(t,h,f)),h=vn(t,i),h!=null&&l.push(da(t,h,f))),t=t.return}return l}function us(t){if(t===null)return null;do t=t.return;while(t&&t.tag!==5);return t||null}function Yd(t,i,a,l,f){for(var h=i._reactName,T=[];a!==null&&a!==l;){var N=a,B=N.alternate,re=N.stateNode;if(B!==null&&B===l)break;N.tag===5&&re!==null&&(N=re,f?(B=vn(a,h),B!=null&&T.unshift(da(a,B,N))):f||(B=vn(a,h),B!=null&&T.push(da(a,B,N)))),a=a.return}T.length!==0&&t.push({event:i,listeners:T})}var l_=/\r\n?/g,u_=/\u0000|\uFFFD/g;function qd(t){return(typeof t=="string"?t:""+t).replace(l_,`
`).replace(u_,"")}function po(t,i,a){if(i=qd(i),qd(t)!==i&&a)throw Error(n(425))}function mo(){}var du=null,hu=null;function pu(t,i){return t==="textarea"||t==="noscript"||typeof i.children=="string"||typeof i.children=="number"||typeof i.dangerouslySetInnerHTML=="object"&&i.dangerouslySetInnerHTML!==null&&i.dangerouslySetInnerHTML.__html!=null}var mu=typeof setTimeout=="function"?setTimeout:void 0,c_=typeof clearTimeout=="function"?clearTimeout:void 0,$d=typeof Promise=="function"?Promise:void 0,f_=typeof queueMicrotask=="function"?queueMicrotask:typeof $d<"u"?function(t){return $d.resolve(null).then(t).catch(d_)}:mu;function d_(t){setTimeout(function(){throw t})}function gu(t,i){var a=i,l=0;do{var f=a.nextSibling;if(t.removeChild(a),f&&f.nodeType===8)if(a=f.data,a==="/$"){if(l===0){t.removeChild(f),na(i);return}l--}else a!=="$"&&a!=="$?"&&a!=="$!"||l++;a=f}while(a);na(i)}function or(t){for(;t!=null;t=t.nextSibling){var i=t.nodeType;if(i===1||i===3)break;if(i===8){if(i=t.data,i==="$"||i==="$!"||i==="$?")break;if(i==="/$")return null}}return t}function Kd(t){t=t.previousSibling;for(var i=0;t;){if(t.nodeType===8){var a=t.data;if(a==="$"||a==="$!"||a==="$?"){if(i===0)return t;i--}else a==="/$"&&i++}t=t.previousSibling}return null}var cs=Math.random().toString(36).slice(2),vi="__reactFiber$"+cs,ha="__reactProps$"+cs,Ii="__reactContainer$"+cs,_u="__reactEvents$"+cs,h_="__reactListeners$"+cs,p_="__reactHandles$"+cs;function Lr(t){var i=t[vi];if(i)return i;for(var a=t.parentNode;a;){if(i=a[Ii]||a[vi]){if(a=i.alternate,i.child!==null||a!==null&&a.child!==null)for(t=Kd(t);t!==null;){if(a=t[vi])return a;t=Kd(t)}return i}t=a,a=t.parentNode}return null}function pa(t){return t=t[vi]||t[Ii],!t||t.tag!==5&&t.tag!==6&&t.tag!==13&&t.tag!==3?null:t}function fs(t){if(t.tag===5||t.tag===6)return t.stateNode;throw Error(n(33))}function go(t){return t[ha]||null}var vu=[],ds=-1;function lr(t){return{current:t}}function Bt(t){0>ds||(t.current=vu[ds],vu[ds]=null,ds--)}function Ut(t,i){ds++,vu[ds]=t.current,t.current=i}var ur={},fn=lr(ur),Cn=lr(!1),Nr=ur;function hs(t,i){var a=t.type.contextTypes;if(!a)return ur;var l=t.stateNode;if(l&&l.__reactInternalMemoizedUnmaskedChildContext===i)return l.__reactInternalMemoizedMaskedChildContext;var f={},h;for(h in a)f[h]=i[h];return l&&(t=t.stateNode,t.__reactInternalMemoizedUnmaskedChildContext=i,t.__reactInternalMemoizedMaskedChildContext=f),f}function Rn(t){return t=t.childContextTypes,t!=null}function _o(){Bt(Cn),Bt(fn)}function Zd(t,i,a){if(fn.current!==ur)throw Error(n(168));Ut(fn,i),Ut(Cn,a)}function Qd(t,i,a){var l=t.stateNode;if(i=i.childContextTypes,typeof l.getChildContext!="function")return a;l=l.getChildContext();for(var f in l)if(!(f in i))throw Error(n(108,me(t)||"Unknown",f));return le({},a,l)}function vo(t){return t=(t=t.stateNode)&&t.__reactInternalMemoizedMergedChildContext||ur,Nr=fn.current,Ut(fn,t),Ut(Cn,Cn.current),!0}function Jd(t,i,a){var l=t.stateNode;if(!l)throw Error(n(169));a?(t=Qd(t,i,Nr),l.__reactInternalMemoizedMergedChildContext=t,Bt(Cn),Bt(fn),Ut(fn,t)):Bt(Cn),Ut(Cn,a)}var Ui=null,xo=!1,xu=!1;function eh(t){Ui===null?Ui=[t]:Ui.push(t)}function m_(t){xo=!0,eh(t)}function cr(){if(!xu&&Ui!==null){xu=!0;var t=0,i=st;try{var a=Ui;for(st=1;t<a.length;t++){var l=a[t];do l=l(!0);while(l!==null)}Ui=null,xo=!1}catch(f){throw Ui!==null&&(Ui=Ui.slice(t+1)),Qa(se,cr),f}finally{st=i,xu=!1}}return null}var ps=[],ms=0,So=null,yo=0,Yn=[],qn=0,Ir=null,Fi=1,Oi="";function Ur(t,i){ps[ms++]=yo,ps[ms++]=So,So=t,yo=i}function th(t,i,a){Yn[qn++]=Fi,Yn[qn++]=Oi,Yn[qn++]=Ir,Ir=t;var l=Fi;t=Oi;var f=32-Je(l)-1;l&=~(1<<f),a+=1;var h=32-Je(i)+f;if(30<h){var T=f-f%5;h=(l&(1<<T)-1).toString(32),l>>=T,f-=T,Fi=1<<32-Je(i)+f|a<<f|l,Oi=h+t}else Fi=1<<h|a<<f|l,Oi=t}function Su(t){t.return!==null&&(Ur(t,1),th(t,1,0))}function yu(t){for(;t===So;)So=ps[--ms],ps[ms]=null,yo=ps[--ms],ps[ms]=null;for(;t===Ir;)Ir=Yn[--qn],Yn[qn]=null,Oi=Yn[--qn],Yn[qn]=null,Fi=Yn[--qn],Yn[qn]=null}var Bn=null,kn=null,zt=!1,ai=null;function nh(t,i){var a=Qn(5,null,null,0);a.elementType="DELETED",a.stateNode=i,a.return=t,i=t.deletions,i===null?(t.deletions=[a],t.flags|=16):i.push(a)}function ih(t,i){switch(t.tag){case 5:var a=t.type;return i=i.nodeType!==1||a.toLowerCase()!==i.nodeName.toLowerCase()?null:i,i!==null?(t.stateNode=i,Bn=t,kn=or(i.firstChild),!0):!1;case 6:return i=t.pendingProps===""||i.nodeType!==3?null:i,i!==null?(t.stateNode=i,Bn=t,kn=null,!0):!1;case 13:return i=i.nodeType!==8?null:i,i!==null?(a=Ir!==null?{id:Fi,overflow:Oi}:null,t.memoizedState={dehydrated:i,treeContext:a,retryLane:1073741824},a=Qn(18,null,null,0),a.stateNode=i,a.return=t,t.child=a,Bn=t,kn=null,!0):!1;default:return!1}}function Mu(t){return(t.mode&1)!==0&&(t.flags&128)===0}function Eu(t){if(zt){var i=kn;if(i){var a=i;if(!ih(t,i)){if(Mu(t))throw Error(n(418));i=or(a.nextSibling);var l=Bn;i&&ih(t,i)?nh(l,a):(t.flags=t.flags&-4097|2,zt=!1,Bn=t)}}else{if(Mu(t))throw Error(n(418));t.flags=t.flags&-4097|2,zt=!1,Bn=t}}}function rh(t){for(t=t.return;t!==null&&t.tag!==5&&t.tag!==3&&t.tag!==13;)t=t.return;Bn=t}function Mo(t){if(t!==Bn)return!1;if(!zt)return rh(t),zt=!0,!1;var i;if((i=t.tag!==3)&&!(i=t.tag!==5)&&(i=t.type,i=i!=="head"&&i!=="body"&&!pu(t.type,t.memoizedProps)),i&&(i=kn)){if(Mu(t))throw sh(),Error(n(418));for(;i;)nh(t,i),i=or(i.nextSibling)}if(rh(t),t.tag===13){if(t=t.memoizedState,t=t!==null?t.dehydrated:null,!t)throw Error(n(317));e:{for(t=t.nextSibling,i=0;t;){if(t.nodeType===8){var a=t.data;if(a==="/$"){if(i===0){kn=or(t.nextSibling);break e}i--}else a!=="$"&&a!=="$!"&&a!=="$?"||i++}t=t.nextSibling}kn=null}}else kn=Bn?or(t.stateNode.nextSibling):null;return!0}function sh(){for(var t=kn;t;)t=or(t.nextSibling)}function gs(){kn=Bn=null,zt=!1}function Tu(t){ai===null?ai=[t]:ai.push(t)}var g_=b.ReactCurrentBatchConfig;function ma(t,i,a){if(t=a.ref,t!==null&&typeof t!="function"&&typeof t!="object"){if(a._owner){if(a=a._owner,a){if(a.tag!==1)throw Error(n(309));var l=a.stateNode}if(!l)throw Error(n(147,t));var f=l,h=""+t;return i!==null&&i.ref!==null&&typeof i.ref=="function"&&i.ref._stringRef===h?i.ref:(i=function(T){var N=f.refs;T===null?delete N[h]:N[h]=T},i._stringRef=h,i)}if(typeof t!="string")throw Error(n(284));if(!a._owner)throw Error(n(290,t))}return t}function Eo(t,i){throw t=Object.prototype.toString.call(i),Error(n(31,t==="[object Object]"?"object with keys {"+Object.keys(i).join(", ")+"}":t))}function ah(t){var i=t._init;return i(t._payload)}function oh(t){function i(Y,H){if(t){var Z=Y.deletions;Z===null?(Y.deletions=[H],Y.flags|=16):Z.push(H)}}function a(Y,H){if(!t)return null;for(;H!==null;)i(Y,H),H=H.sibling;return null}function l(Y,H){for(Y=new Map;H!==null;)H.key!==null?Y.set(H.key,H):Y.set(H.index,H),H=H.sibling;return Y}function f(Y,H){return Y=vr(Y,H),Y.index=0,Y.sibling=null,Y}function h(Y,H,Z){return Y.index=Z,t?(Z=Y.alternate,Z!==null?(Z=Z.index,Z<H?(Y.flags|=2,H):Z):(Y.flags|=2,H)):(Y.flags|=1048576,H)}function T(Y){return t&&Y.alternate===null&&(Y.flags|=2),Y}function N(Y,H,Z,Ee){return H===null||H.tag!==6?(H=mc(Z,Y.mode,Ee),H.return=Y,H):(H=f(H,Z),H.return=Y,H)}function B(Y,H,Z,Ee){var $e=Z.type;return $e===z?ve(Y,H,Z.props.children,Ee,Z.key):H!==null&&(H.elementType===$e||typeof $e=="object"&&$e!==null&&$e.$$typeof===ee&&ah($e)===H.type)?(Ee=f(H,Z.props),Ee.ref=ma(Y,H,Z),Ee.return=Y,Ee):(Ee=Yo(Z.type,Z.key,Z.props,null,Y.mode,Ee),Ee.ref=ma(Y,H,Z),Ee.return=Y,Ee)}function re(Y,H,Z,Ee){return H===null||H.tag!==4||H.stateNode.containerInfo!==Z.containerInfo||H.stateNode.implementation!==Z.implementation?(H=gc(Z,Y.mode,Ee),H.return=Y,H):(H=f(H,Z.children||[]),H.return=Y,H)}function ve(Y,H,Z,Ee,$e){return H===null||H.tag!==7?(H=Gr(Z,Y.mode,Ee,$e),H.return=Y,H):(H=f(H,Z),H.return=Y,H)}function xe(Y,H,Z){if(typeof H=="string"&&H!==""||typeof H=="number")return H=mc(""+H,Y.mode,Z),H.return=Y,H;if(typeof H=="object"&&H!==null){switch(H.$$typeof){case F:return Z=Yo(H.type,H.key,H.props,null,Y.mode,Z),Z.ref=ma(Y,null,H),Z.return=Y,Z;case U:return H=gc(H,Y.mode,Z),H.return=Y,H;case ee:var Ee=H._init;return xe(Y,Ee(H._payload),Z)}if(mt(H)||ae(H))return H=Gr(H,Y.mode,Z,null),H.return=Y,H;Eo(Y,H)}return null}function _e(Y,H,Z,Ee){var $e=H!==null?H.key:null;if(typeof Z=="string"&&Z!==""||typeof Z=="number")return $e!==null?null:N(Y,H,""+Z,Ee);if(typeof Z=="object"&&Z!==null){switch(Z.$$typeof){case F:return Z.key===$e?B(Y,H,Z,Ee):null;case U:return Z.key===$e?re(Y,H,Z,Ee):null;case ee:return $e=Z._init,_e(Y,H,$e(Z._payload),Ee)}if(mt(Z)||ae(Z))return $e!==null?null:ve(Y,H,Z,Ee,null);Eo(Y,Z)}return null}function Ie(Y,H,Z,Ee,$e){if(typeof Ee=="string"&&Ee!==""||typeof Ee=="number")return Y=Y.get(Z)||null,N(H,Y,""+Ee,$e);if(typeof Ee=="object"&&Ee!==null){switch(Ee.$$typeof){case F:return Y=Y.get(Ee.key===null?Z:Ee.key)||null,B(H,Y,Ee,$e);case U:return Y=Y.get(Ee.key===null?Z:Ee.key)||null,re(H,Y,Ee,$e);case ee:var et=Ee._init;return Ie(Y,H,Z,et(Ee._payload),$e)}if(mt(Ee)||ae(Ee))return Y=Y.get(Z)||null,ve(H,Y,Ee,$e,null);Eo(H,Ee)}return null}function Ve(Y,H,Z,Ee){for(var $e=null,et=null,tt=H,at=H=0,an=null;tt!==null&&at<Z.length;at++){tt.index>at?(an=tt,tt=null):an=tt.sibling;var Tt=_e(Y,tt,Z[at],Ee);if(Tt===null){tt===null&&(tt=an);break}t&&tt&&Tt.alternate===null&&i(Y,tt),H=h(Tt,H,at),et===null?$e=Tt:et.sibling=Tt,et=Tt,tt=an}if(at===Z.length)return a(Y,tt),zt&&Ur(Y,at),$e;if(tt===null){for(;at<Z.length;at++)tt=xe(Y,Z[at],Ee),tt!==null&&(H=h(tt,H,at),et===null?$e=tt:et.sibling=tt,et=tt);return zt&&Ur(Y,at),$e}for(tt=l(Y,tt);at<Z.length;at++)an=Ie(tt,Y,at,Z[at],Ee),an!==null&&(t&&an.alternate!==null&&tt.delete(an.key===null?at:an.key),H=h(an,H,at),et===null?$e=an:et.sibling=an,et=an);return t&&tt.forEach(function(xr){return i(Y,xr)}),zt&&Ur(Y,at),$e}function je(Y,H,Z,Ee){var $e=ae(Z);if(typeof $e!="function")throw Error(n(150));if(Z=$e.call(Z),Z==null)throw Error(n(151));for(var et=$e=null,tt=H,at=H=0,an=null,Tt=Z.next();tt!==null&&!Tt.done;at++,Tt=Z.next()){tt.index>at?(an=tt,tt=null):an=tt.sibling;var xr=_e(Y,tt,Tt.value,Ee);if(xr===null){tt===null&&(tt=an);break}t&&tt&&xr.alternate===null&&i(Y,tt),H=h(xr,H,at),et===null?$e=xr:et.sibling=xr,et=xr,tt=an}if(Tt.done)return a(Y,tt),zt&&Ur(Y,at),$e;if(tt===null){for(;!Tt.done;at++,Tt=Z.next())Tt=xe(Y,Tt.value,Ee),Tt!==null&&(H=h(Tt,H,at),et===null?$e=Tt:et.sibling=Tt,et=Tt);return zt&&Ur(Y,at),$e}for(tt=l(Y,tt);!Tt.done;at++,Tt=Z.next())Tt=Ie(tt,Y,at,Tt.value,Ee),Tt!==null&&(t&&Tt.alternate!==null&&tt.delete(Tt.key===null?at:Tt.key),H=h(Tt,H,at),et===null?$e=Tt:et.sibling=Tt,et=Tt);return t&&tt.forEach(function($_){return i(Y,$_)}),zt&&Ur(Y,at),$e}function Yt(Y,H,Z,Ee){if(typeof Z=="object"&&Z!==null&&Z.type===z&&Z.key===null&&(Z=Z.props.children),typeof Z=="object"&&Z!==null){switch(Z.$$typeof){case F:e:{for(var $e=Z.key,et=H;et!==null;){if(et.key===$e){if($e=Z.type,$e===z){if(et.tag===7){a(Y,et.sibling),H=f(et,Z.props.children),H.return=Y,Y=H;break e}}else if(et.elementType===$e||typeof $e=="object"&&$e!==null&&$e.$$typeof===ee&&ah($e)===et.type){a(Y,et.sibling),H=f(et,Z.props),H.ref=ma(Y,et,Z),H.return=Y,Y=H;break e}a(Y,et);break}else i(Y,et);et=et.sibling}Z.type===z?(H=Gr(Z.props.children,Y.mode,Ee,Z.key),H.return=Y,Y=H):(Ee=Yo(Z.type,Z.key,Z.props,null,Y.mode,Ee),Ee.ref=ma(Y,H,Z),Ee.return=Y,Y=Ee)}return T(Y);case U:e:{for(et=Z.key;H!==null;){if(H.key===et)if(H.tag===4&&H.stateNode.containerInfo===Z.containerInfo&&H.stateNode.implementation===Z.implementation){a(Y,H.sibling),H=f(H,Z.children||[]),H.return=Y,Y=H;break e}else{a(Y,H);break}else i(Y,H);H=H.sibling}H=gc(Z,Y.mode,Ee),H.return=Y,Y=H}return T(Y);case ee:return et=Z._init,Yt(Y,H,et(Z._payload),Ee)}if(mt(Z))return Ve(Y,H,Z,Ee);if(ae(Z))return je(Y,H,Z,Ee);Eo(Y,Z)}return typeof Z=="string"&&Z!==""||typeof Z=="number"?(Z=""+Z,H!==null&&H.tag===6?(a(Y,H.sibling),H=f(H,Z),H.return=Y,Y=H):(a(Y,H),H=mc(Z,Y.mode,Ee),H.return=Y,Y=H),T(Y)):a(Y,H)}return Yt}var _s=oh(!0),lh=oh(!1),To=lr(null),wo=null,vs=null,wu=null;function Au(){wu=vs=wo=null}function Cu(t){var i=To.current;Bt(To),t._currentValue=i}function Ru(t,i,a){for(;t!==null;){var l=t.alternate;if((t.childLanes&i)!==i?(t.childLanes|=i,l!==null&&(l.childLanes|=i)):l!==null&&(l.childLanes&i)!==i&&(l.childLanes|=i),t===a)break;t=t.return}}function xs(t,i){wo=t,wu=vs=null,t=t.dependencies,t!==null&&t.firstContext!==null&&((t.lanes&i)!==0&&(bn=!0),t.firstContext=null)}function $n(t){var i=t._currentValue;if(wu!==t)if(t={context:t,memoizedValue:i,next:null},vs===null){if(wo===null)throw Error(n(308));vs=t,wo.dependencies={lanes:0,firstContext:t}}else vs=vs.next=t;return i}var Fr=null;function bu(t){Fr===null?Fr=[t]:Fr.push(t)}function uh(t,i,a,l){var f=i.interleaved;return f===null?(a.next=a,bu(i)):(a.next=f.next,f.next=a),i.interleaved=a,Bi(t,l)}function Bi(t,i){t.lanes|=i;var a=t.alternate;for(a!==null&&(a.lanes|=i),a=t,t=t.return;t!==null;)t.childLanes|=i,a=t.alternate,a!==null&&(a.childLanes|=i),a=t,t=t.return;return a.tag===3?a.stateNode:null}var fr=!1;function Pu(t){t.updateQueue={baseState:t.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,interleaved:null,lanes:0},effects:null}}function ch(t,i){t=t.updateQueue,i.updateQueue===t&&(i.updateQueue={baseState:t.baseState,firstBaseUpdate:t.firstBaseUpdate,lastBaseUpdate:t.lastBaseUpdate,shared:t.shared,effects:t.effects})}function ki(t,i){return{eventTime:t,lane:i,tag:0,payload:null,callback:null,next:null}}function dr(t,i,a){var l=t.updateQueue;if(l===null)return null;if(l=l.shared,(Mt&2)!==0){var f=l.pending;return f===null?i.next=i:(i.next=f.next,f.next=i),l.pending=i,Bi(t,a)}return f=l.interleaved,f===null?(i.next=i,bu(l)):(i.next=f.next,f.next=i),l.interleaved=i,Bi(t,a)}function Ao(t,i,a){if(i=i.updateQueue,i!==null&&(i=i.shared,(a&4194240)!==0)){var l=i.lanes;l&=t.pendingLanes,a|=l,i.lanes=a,At(t,a)}}function fh(t,i){var a=t.updateQueue,l=t.alternate;if(l!==null&&(l=l.updateQueue,a===l)){var f=null,h=null;if(a=a.firstBaseUpdate,a!==null){do{var T={eventTime:a.eventTime,lane:a.lane,tag:a.tag,payload:a.payload,callback:a.callback,next:null};h===null?f=h=T:h=h.next=T,a=a.next}while(a!==null);h===null?f=h=i:h=h.next=i}else f=h=i;a={baseState:l.baseState,firstBaseUpdate:f,lastBaseUpdate:h,shared:l.shared,effects:l.effects},t.updateQueue=a;return}t=a.lastBaseUpdate,t===null?a.firstBaseUpdate=i:t.next=i,a.lastBaseUpdate=i}function Co(t,i,a,l){var f=t.updateQueue;fr=!1;var h=f.firstBaseUpdate,T=f.lastBaseUpdate,N=f.shared.pending;if(N!==null){f.shared.pending=null;var B=N,re=B.next;B.next=null,T===null?h=re:T.next=re,T=B;var ve=t.alternate;ve!==null&&(ve=ve.updateQueue,N=ve.lastBaseUpdate,N!==T&&(N===null?ve.firstBaseUpdate=re:N.next=re,ve.lastBaseUpdate=B))}if(h!==null){var xe=f.baseState;T=0,ve=re=B=null,N=h;do{var _e=N.lane,Ie=N.eventTime;if((l&_e)===_e){ve!==null&&(ve=ve.next={eventTime:Ie,lane:0,tag:N.tag,payload:N.payload,callback:N.callback,next:null});e:{var Ve=t,je=N;switch(_e=i,Ie=a,je.tag){case 1:if(Ve=je.payload,typeof Ve=="function"){xe=Ve.call(Ie,xe,_e);break e}xe=Ve;break e;case 3:Ve.flags=Ve.flags&-65537|128;case 0:if(Ve=je.payload,_e=typeof Ve=="function"?Ve.call(Ie,xe,_e):Ve,_e==null)break e;xe=le({},xe,_e);break e;case 2:fr=!0}}N.callback!==null&&N.lane!==0&&(t.flags|=64,_e=f.effects,_e===null?f.effects=[N]:_e.push(N))}else Ie={eventTime:Ie,lane:_e,tag:N.tag,payload:N.payload,callback:N.callback,next:null},ve===null?(re=ve=Ie,B=xe):ve=ve.next=Ie,T|=_e;if(N=N.next,N===null){if(N=f.shared.pending,N===null)break;_e=N,N=_e.next,_e.next=null,f.lastBaseUpdate=_e,f.shared.pending=null}}while(!0);if(ve===null&&(B=xe),f.baseState=B,f.firstBaseUpdate=re,f.lastBaseUpdate=ve,i=f.shared.interleaved,i!==null){f=i;do T|=f.lane,f=f.next;while(f!==i)}else h===null&&(f.shared.lanes=0);kr|=T,t.lanes=T,t.memoizedState=xe}}function dh(t,i,a){if(t=i.effects,i.effects=null,t!==null)for(i=0;i<t.length;i++){var l=t[i],f=l.callback;if(f!==null){if(l.callback=null,l=a,typeof f!="function")throw Error(n(191,f));f.call(l)}}}var ga={},xi=lr(ga),_a=lr(ga),va=lr(ga);function Or(t){if(t===ga)throw Error(n(174));return t}function Du(t,i){switch(Ut(va,i),Ut(_a,t),Ut(xi,ga),t=i.nodeType,t){case 9:case 11:i=(i=i.documentElement)?i.namespaceURI:ge(null,"");break;default:t=t===8?i.parentNode:i,i=t.namespaceURI||null,t=t.tagName,i=ge(i,t)}Bt(xi),Ut(xi,i)}function Ss(){Bt(xi),Bt(_a),Bt(va)}function hh(t){Or(va.current);var i=Or(xi.current),a=ge(i,t.type);i!==a&&(Ut(_a,t),Ut(xi,a))}function Lu(t){_a.current===t&&(Bt(xi),Bt(_a))}var Vt=lr(0);function Ro(t){for(var i=t;i!==null;){if(i.tag===13){var a=i.memoizedState;if(a!==null&&(a=a.dehydrated,a===null||a.data==="$?"||a.data==="$!"))return i}else if(i.tag===19&&i.memoizedProps.revealOrder!==void 0){if((i.flags&128)!==0)return i}else if(i.child!==null){i.child.return=i,i=i.child;continue}if(i===t)break;for(;i.sibling===null;){if(i.return===null||i.return===t)return null;i=i.return}i.sibling.return=i.return,i=i.sibling}return null}var Nu=[];function Iu(){for(var t=0;t<Nu.length;t++)Nu[t]._workInProgressVersionPrimary=null;Nu.length=0}var bo=b.ReactCurrentDispatcher,Uu=b.ReactCurrentBatchConfig,Br=0,Ht=null,Jt=null,rn=null,Po=!1,xa=!1,Sa=0,__=0;function dn(){throw Error(n(321))}function Fu(t,i){if(i===null)return!1;for(var a=0;a<i.length&&a<t.length;a++)if(!si(t[a],i[a]))return!1;return!0}function Ou(t,i,a,l,f,h){if(Br=h,Ht=i,i.memoizedState=null,i.updateQueue=null,i.lanes=0,bo.current=t===null||t.memoizedState===null?y_:M_,t=a(l,f),xa){h=0;do{if(xa=!1,Sa=0,25<=h)throw Error(n(301));h+=1,rn=Jt=null,i.updateQueue=null,bo.current=E_,t=a(l,f)}while(xa)}if(bo.current=No,i=Jt!==null&&Jt.next!==null,Br=0,rn=Jt=Ht=null,Po=!1,i)throw Error(n(300));return t}function Bu(){var t=Sa!==0;return Sa=0,t}function Si(){var t={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return rn===null?Ht.memoizedState=rn=t:rn=rn.next=t,rn}function Kn(){if(Jt===null){var t=Ht.alternate;t=t!==null?t.memoizedState:null}else t=Jt.next;var i=rn===null?Ht.memoizedState:rn.next;if(i!==null)rn=i,Jt=t;else{if(t===null)throw Error(n(310));Jt=t,t={memoizedState:Jt.memoizedState,baseState:Jt.baseState,baseQueue:Jt.baseQueue,queue:Jt.queue,next:null},rn===null?Ht.memoizedState=rn=t:rn=rn.next=t}return rn}function ya(t,i){return typeof i=="function"?i(t):i}function ku(t){var i=Kn(),a=i.queue;if(a===null)throw Error(n(311));a.lastRenderedReducer=t;var l=Jt,f=l.baseQueue,h=a.pending;if(h!==null){if(f!==null){var T=f.next;f.next=h.next,h.next=T}l.baseQueue=f=h,a.pending=null}if(f!==null){h=f.next,l=l.baseState;var N=T=null,B=null,re=h;do{var ve=re.lane;if((Br&ve)===ve)B!==null&&(B=B.next={lane:0,action:re.action,hasEagerState:re.hasEagerState,eagerState:re.eagerState,next:null}),l=re.hasEagerState?re.eagerState:t(l,re.action);else{var xe={lane:ve,action:re.action,hasEagerState:re.hasEagerState,eagerState:re.eagerState,next:null};B===null?(N=B=xe,T=l):B=B.next=xe,Ht.lanes|=ve,kr|=ve}re=re.next}while(re!==null&&re!==h);B===null?T=l:B.next=N,si(l,i.memoizedState)||(bn=!0),i.memoizedState=l,i.baseState=T,i.baseQueue=B,a.lastRenderedState=l}if(t=a.interleaved,t!==null){f=t;do h=f.lane,Ht.lanes|=h,kr|=h,f=f.next;while(f!==t)}else f===null&&(a.lanes=0);return[i.memoizedState,a.dispatch]}function zu(t){var i=Kn(),a=i.queue;if(a===null)throw Error(n(311));a.lastRenderedReducer=t;var l=a.dispatch,f=a.pending,h=i.memoizedState;if(f!==null){a.pending=null;var T=f=f.next;do h=t(h,T.action),T=T.next;while(T!==f);si(h,i.memoizedState)||(bn=!0),i.memoizedState=h,i.baseQueue===null&&(i.baseState=h),a.lastRenderedState=h}return[h,l]}function ph(){}function mh(t,i){var a=Ht,l=Kn(),f=i(),h=!si(l.memoizedState,f);if(h&&(l.memoizedState=f,bn=!0),l=l.queue,Vu(vh.bind(null,a,l,t),[t]),l.getSnapshot!==i||h||rn!==null&&rn.memoizedState.tag&1){if(a.flags|=2048,Ma(9,_h.bind(null,a,l,f,i),void 0,null),sn===null)throw Error(n(349));(Br&30)!==0||gh(a,i,f)}return f}function gh(t,i,a){t.flags|=16384,t={getSnapshot:i,value:a},i=Ht.updateQueue,i===null?(i={lastEffect:null,stores:null},Ht.updateQueue=i,i.stores=[t]):(a=i.stores,a===null?i.stores=[t]:a.push(t))}function _h(t,i,a,l){i.value=a,i.getSnapshot=l,xh(i)&&Sh(t)}function vh(t,i,a){return a(function(){xh(i)&&Sh(t)})}function xh(t){var i=t.getSnapshot;t=t.value;try{var a=i();return!si(t,a)}catch{return!0}}function Sh(t){var i=Bi(t,1);i!==null&&ci(i,t,1,-1)}function yh(t){var i=Si();return typeof t=="function"&&(t=t()),i.memoizedState=i.baseState=t,t={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:ya,lastRenderedState:t},i.queue=t,t=t.dispatch=S_.bind(null,Ht,t),[i.memoizedState,t]}function Ma(t,i,a,l){return t={tag:t,create:i,destroy:a,deps:l,next:null},i=Ht.updateQueue,i===null?(i={lastEffect:null,stores:null},Ht.updateQueue=i,i.lastEffect=t.next=t):(a=i.lastEffect,a===null?i.lastEffect=t.next=t:(l=a.next,a.next=t,t.next=l,i.lastEffect=t)),t}function Mh(){return Kn().memoizedState}function Do(t,i,a,l){var f=Si();Ht.flags|=t,f.memoizedState=Ma(1|i,a,void 0,l===void 0?null:l)}function Lo(t,i,a,l){var f=Kn();l=l===void 0?null:l;var h=void 0;if(Jt!==null){var T=Jt.memoizedState;if(h=T.destroy,l!==null&&Fu(l,T.deps)){f.memoizedState=Ma(i,a,h,l);return}}Ht.flags|=t,f.memoizedState=Ma(1|i,a,h,l)}function Eh(t,i){return Do(8390656,8,t,i)}function Vu(t,i){return Lo(2048,8,t,i)}function Th(t,i){return Lo(4,2,t,i)}function wh(t,i){return Lo(4,4,t,i)}function Ah(t,i){if(typeof i=="function")return t=t(),i(t),function(){i(null)};if(i!=null)return t=t(),i.current=t,function(){i.current=null}}function Ch(t,i,a){return a=a!=null?a.concat([t]):null,Lo(4,4,Ah.bind(null,i,t),a)}function Hu(){}function Rh(t,i){var a=Kn();i=i===void 0?null:i;var l=a.memoizedState;return l!==null&&i!==null&&Fu(i,l[1])?l[0]:(a.memoizedState=[t,i],t)}function bh(t,i){var a=Kn();i=i===void 0?null:i;var l=a.memoizedState;return l!==null&&i!==null&&Fu(i,l[1])?l[0]:(t=t(),a.memoizedState=[t,i],t)}function Ph(t,i,a){return(Br&21)===0?(t.baseState&&(t.baseState=!1,bn=!0),t.memoizedState=a):(si(a,i)||(a=wn(),Ht.lanes|=a,kr|=a,t.baseState=!0),i)}function v_(t,i){var a=st;st=a!==0&&4>a?a:4,t(!0);var l=Uu.transition;Uu.transition={};try{t(!1),i()}finally{st=a,Uu.transition=l}}function Dh(){return Kn().memoizedState}function x_(t,i,a){var l=gr(t);if(a={lane:l,action:a,hasEagerState:!1,eagerState:null,next:null},Lh(t))Nh(i,a);else if(a=uh(t,i,a,l),a!==null){var f=yn();ci(a,t,l,f),Ih(a,i,l)}}function S_(t,i,a){var l=gr(t),f={lane:l,action:a,hasEagerState:!1,eagerState:null,next:null};if(Lh(t))Nh(i,f);else{var h=t.alternate;if(t.lanes===0&&(h===null||h.lanes===0)&&(h=i.lastRenderedReducer,h!==null))try{var T=i.lastRenderedState,N=h(T,a);if(f.hasEagerState=!0,f.eagerState=N,si(N,T)){var B=i.interleaved;B===null?(f.next=f,bu(i)):(f.next=B.next,B.next=f),i.interleaved=f;return}}catch{}finally{}a=uh(t,i,f,l),a!==null&&(f=yn(),ci(a,t,l,f),Ih(a,i,l))}}function Lh(t){var i=t.alternate;return t===Ht||i!==null&&i===Ht}function Nh(t,i){xa=Po=!0;var a=t.pending;a===null?i.next=i:(i.next=a.next,a.next=i),t.pending=i}function Ih(t,i,a){if((a&4194240)!==0){var l=i.lanes;l&=t.pendingLanes,a|=l,i.lanes=a,At(t,a)}}var No={readContext:$n,useCallback:dn,useContext:dn,useEffect:dn,useImperativeHandle:dn,useInsertionEffect:dn,useLayoutEffect:dn,useMemo:dn,useReducer:dn,useRef:dn,useState:dn,useDebugValue:dn,useDeferredValue:dn,useTransition:dn,useMutableSource:dn,useSyncExternalStore:dn,useId:dn,unstable_isNewReconciler:!1},y_={readContext:$n,useCallback:function(t,i){return Si().memoizedState=[t,i===void 0?null:i],t},useContext:$n,useEffect:Eh,useImperativeHandle:function(t,i,a){return a=a!=null?a.concat([t]):null,Do(4194308,4,Ah.bind(null,i,t),a)},useLayoutEffect:function(t,i){return Do(4194308,4,t,i)},useInsertionEffect:function(t,i){return Do(4,2,t,i)},useMemo:function(t,i){var a=Si();return i=i===void 0?null:i,t=t(),a.memoizedState=[t,i],t},useReducer:function(t,i,a){var l=Si();return i=a!==void 0?a(i):i,l.memoizedState=l.baseState=i,t={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:t,lastRenderedState:i},l.queue=t,t=t.dispatch=x_.bind(null,Ht,t),[l.memoizedState,t]},useRef:function(t){var i=Si();return t={current:t},i.memoizedState=t},useState:yh,useDebugValue:Hu,useDeferredValue:function(t){return Si().memoizedState=t},useTransition:function(){var t=yh(!1),i=t[0];return t=v_.bind(null,t[1]),Si().memoizedState=t,[i,t]},useMutableSource:function(){},useSyncExternalStore:function(t,i,a){var l=Ht,f=Si();if(zt){if(a===void 0)throw Error(n(407));a=a()}else{if(a=i(),sn===null)throw Error(n(349));(Br&30)!==0||gh(l,i,a)}f.memoizedState=a;var h={value:a,getSnapshot:i};return f.queue=h,Eh(vh.bind(null,l,h,t),[t]),l.flags|=2048,Ma(9,_h.bind(null,l,h,a,i),void 0,null),a},useId:function(){var t=Si(),i=sn.identifierPrefix;if(zt){var a=Oi,l=Fi;a=(l&~(1<<32-Je(l)-1)).toString(32)+a,i=":"+i+"R"+a,a=Sa++,0<a&&(i+="H"+a.toString(32)),i+=":"}else a=__++,i=":"+i+"r"+a.toString(32)+":";return t.memoizedState=i},unstable_isNewReconciler:!1},M_={readContext:$n,useCallback:Rh,useContext:$n,useEffect:Vu,useImperativeHandle:Ch,useInsertionEffect:Th,useLayoutEffect:wh,useMemo:bh,useReducer:ku,useRef:Mh,useState:function(){return ku(ya)},useDebugValue:Hu,useDeferredValue:function(t){var i=Kn();return Ph(i,Jt.memoizedState,t)},useTransition:function(){var t=ku(ya)[0],i=Kn().memoizedState;return[t,i]},useMutableSource:ph,useSyncExternalStore:mh,useId:Dh,unstable_isNewReconciler:!1},E_={readContext:$n,useCallback:Rh,useContext:$n,useEffect:Vu,useImperativeHandle:Ch,useInsertionEffect:Th,useLayoutEffect:wh,useMemo:bh,useReducer:zu,useRef:Mh,useState:function(){return zu(ya)},useDebugValue:Hu,useDeferredValue:function(t){var i=Kn();return Jt===null?i.memoizedState=t:Ph(i,Jt.memoizedState,t)},useTransition:function(){var t=zu(ya)[0],i=Kn().memoizedState;return[t,i]},useMutableSource:ph,useSyncExternalStore:mh,useId:Dh,unstable_isNewReconciler:!1};function oi(t,i){if(t&&t.defaultProps){i=le({},i),t=t.defaultProps;for(var a in t)i[a]===void 0&&(i[a]=t[a]);return i}return i}function Gu(t,i,a,l){i=t.memoizedState,a=a(l,i),a=a==null?i:le({},i,a),t.memoizedState=a,t.lanes===0&&(t.updateQueue.baseState=a)}var Io={isMounted:function(t){return(t=t._reactInternals)?_i(t)===t:!1},enqueueSetState:function(t,i,a){t=t._reactInternals;var l=yn(),f=gr(t),h=ki(l,f);h.payload=i,a!=null&&(h.callback=a),i=dr(t,h,f),i!==null&&(ci(i,t,f,l),Ao(i,t,f))},enqueueReplaceState:function(t,i,a){t=t._reactInternals;var l=yn(),f=gr(t),h=ki(l,f);h.tag=1,h.payload=i,a!=null&&(h.callback=a),i=dr(t,h,f),i!==null&&(ci(i,t,f,l),Ao(i,t,f))},enqueueForceUpdate:function(t,i){t=t._reactInternals;var a=yn(),l=gr(t),f=ki(a,l);f.tag=2,i!=null&&(f.callback=i),i=dr(t,f,l),i!==null&&(ci(i,t,l,a),Ao(i,t,l))}};function Uh(t,i,a,l,f,h,T){return t=t.stateNode,typeof t.shouldComponentUpdate=="function"?t.shouldComponentUpdate(l,h,T):i.prototype&&i.prototype.isPureReactComponent?!la(a,l)||!la(f,h):!0}function Fh(t,i,a){var l=!1,f=ur,h=i.contextType;return typeof h=="object"&&h!==null?h=$n(h):(f=Rn(i)?Nr:fn.current,l=i.contextTypes,h=(l=l!=null)?hs(t,f):ur),i=new i(a,h),t.memoizedState=i.state!==null&&i.state!==void 0?i.state:null,i.updater=Io,t.stateNode=i,i._reactInternals=t,l&&(t=t.stateNode,t.__reactInternalMemoizedUnmaskedChildContext=f,t.__reactInternalMemoizedMaskedChildContext=h),i}function Oh(t,i,a,l){t=i.state,typeof i.componentWillReceiveProps=="function"&&i.componentWillReceiveProps(a,l),typeof i.UNSAFE_componentWillReceiveProps=="function"&&i.UNSAFE_componentWillReceiveProps(a,l),i.state!==t&&Io.enqueueReplaceState(i,i.state,null)}function Wu(t,i,a,l){var f=t.stateNode;f.props=a,f.state=t.memoizedState,f.refs={},Pu(t);var h=i.contextType;typeof h=="object"&&h!==null?f.context=$n(h):(h=Rn(i)?Nr:fn.current,f.context=hs(t,h)),f.state=t.memoizedState,h=i.getDerivedStateFromProps,typeof h=="function"&&(Gu(t,i,h,a),f.state=t.memoizedState),typeof i.getDerivedStateFromProps=="function"||typeof f.getSnapshotBeforeUpdate=="function"||typeof f.UNSAFE_componentWillMount!="function"&&typeof f.componentWillMount!="function"||(i=f.state,typeof f.componentWillMount=="function"&&f.componentWillMount(),typeof f.UNSAFE_componentWillMount=="function"&&f.UNSAFE_componentWillMount(),i!==f.state&&Io.enqueueReplaceState(f,f.state,null),Co(t,a,f,l),f.state=t.memoizedState),typeof f.componentDidMount=="function"&&(t.flags|=4194308)}function ys(t,i){try{var a="",l=i;do a+=Ze(l),l=l.return;while(l);var f=a}catch(h){f=`
Error generating stack: `+h.message+`
`+h.stack}return{value:t,source:i,stack:f,digest:null}}function Xu(t,i,a){return{value:t,source:null,stack:a??null,digest:i??null}}function ju(t,i){try{console.error(i.value)}catch(a){setTimeout(function(){throw a})}}var T_=typeof WeakMap=="function"?WeakMap:Map;function Bh(t,i,a){a=ki(-1,a),a.tag=3,a.payload={element:null};var l=i.value;return a.callback=function(){Vo||(Vo=!0,oc=l),ju(t,i)},a}function kh(t,i,a){a=ki(-1,a),a.tag=3;var l=t.type.getDerivedStateFromError;if(typeof l=="function"){var f=i.value;a.payload=function(){return l(f)},a.callback=function(){ju(t,i)}}var h=t.stateNode;return h!==null&&typeof h.componentDidCatch=="function"&&(a.callback=function(){ju(t,i),typeof l!="function"&&(pr===null?pr=new Set([this]):pr.add(this));var T=i.stack;this.componentDidCatch(i.value,{componentStack:T!==null?T:""})}),a}function zh(t,i,a){var l=t.pingCache;if(l===null){l=t.pingCache=new T_;var f=new Set;l.set(i,f)}else f=l.get(i),f===void 0&&(f=new Set,l.set(i,f));f.has(a)||(f.add(a),t=B_.bind(null,t,i,a),i.then(t,t))}function Vh(t){do{var i;if((i=t.tag===13)&&(i=t.memoizedState,i=i!==null?i.dehydrated!==null:!0),i)return t;t=t.return}while(t!==null);return null}function Hh(t,i,a,l,f){return(t.mode&1)===0?(t===i?t.flags|=65536:(t.flags|=128,a.flags|=131072,a.flags&=-52805,a.tag===1&&(a.alternate===null?a.tag=17:(i=ki(-1,1),i.tag=2,dr(a,i,1))),a.lanes|=1),t):(t.flags|=65536,t.lanes=f,t)}var w_=b.ReactCurrentOwner,bn=!1;function Sn(t,i,a,l){i.child=t===null?lh(i,null,a,l):_s(i,t.child,a,l)}function Gh(t,i,a,l,f){a=a.render;var h=i.ref;return xs(i,f),l=Ou(t,i,a,l,h,f),a=Bu(),t!==null&&!bn?(i.updateQueue=t.updateQueue,i.flags&=-2053,t.lanes&=~f,zi(t,i,f)):(zt&&a&&Su(i),i.flags|=1,Sn(t,i,l,f),i.child)}function Wh(t,i,a,l,f){if(t===null){var h=a.type;return typeof h=="function"&&!pc(h)&&h.defaultProps===void 0&&a.compare===null&&a.defaultProps===void 0?(i.tag=15,i.type=h,Xh(t,i,h,l,f)):(t=Yo(a.type,null,l,i,i.mode,f),t.ref=i.ref,t.return=i,i.child=t)}if(h=t.child,(t.lanes&f)===0){var T=h.memoizedProps;if(a=a.compare,a=a!==null?a:la,a(T,l)&&t.ref===i.ref)return zi(t,i,f)}return i.flags|=1,t=vr(h,l),t.ref=i.ref,t.return=i,i.child=t}function Xh(t,i,a,l,f){if(t!==null){var h=t.memoizedProps;if(la(h,l)&&t.ref===i.ref)if(bn=!1,i.pendingProps=l=h,(t.lanes&f)!==0)(t.flags&131072)!==0&&(bn=!0);else return i.lanes=t.lanes,zi(t,i,f)}return Yu(t,i,a,l,f)}function jh(t,i,a){var l=i.pendingProps,f=l.children,h=t!==null?t.memoizedState:null;if(l.mode==="hidden")if((i.mode&1)===0)i.memoizedState={baseLanes:0,cachePool:null,transitions:null},Ut(Es,zn),zn|=a;else{if((a&1073741824)===0)return t=h!==null?h.baseLanes|a:a,i.lanes=i.childLanes=1073741824,i.memoizedState={baseLanes:t,cachePool:null,transitions:null},i.updateQueue=null,Ut(Es,zn),zn|=t,null;i.memoizedState={baseLanes:0,cachePool:null,transitions:null},l=h!==null?h.baseLanes:a,Ut(Es,zn),zn|=l}else h!==null?(l=h.baseLanes|a,i.memoizedState=null):l=a,Ut(Es,zn),zn|=l;return Sn(t,i,f,a),i.child}function Yh(t,i){var a=i.ref;(t===null&&a!==null||t!==null&&t.ref!==a)&&(i.flags|=512,i.flags|=2097152)}function Yu(t,i,a,l,f){var h=Rn(a)?Nr:fn.current;return h=hs(i,h),xs(i,f),a=Ou(t,i,a,l,h,f),l=Bu(),t!==null&&!bn?(i.updateQueue=t.updateQueue,i.flags&=-2053,t.lanes&=~f,zi(t,i,f)):(zt&&l&&Su(i),i.flags|=1,Sn(t,i,a,f),i.child)}function qh(t,i,a,l,f){if(Rn(a)){var h=!0;vo(i)}else h=!1;if(xs(i,f),i.stateNode===null)Fo(t,i),Fh(i,a,l),Wu(i,a,l,f),l=!0;else if(t===null){var T=i.stateNode,N=i.memoizedProps;T.props=N;var B=T.context,re=a.contextType;typeof re=="object"&&re!==null?re=$n(re):(re=Rn(a)?Nr:fn.current,re=hs(i,re));var ve=a.getDerivedStateFromProps,xe=typeof ve=="function"||typeof T.getSnapshotBeforeUpdate=="function";xe||typeof T.UNSAFE_componentWillReceiveProps!="function"&&typeof T.componentWillReceiveProps!="function"||(N!==l||B!==re)&&Oh(i,T,l,re),fr=!1;var _e=i.memoizedState;T.state=_e,Co(i,l,T,f),B=i.memoizedState,N!==l||_e!==B||Cn.current||fr?(typeof ve=="function"&&(Gu(i,a,ve,l),B=i.memoizedState),(N=fr||Uh(i,a,N,l,_e,B,re))?(xe||typeof T.UNSAFE_componentWillMount!="function"&&typeof T.componentWillMount!="function"||(typeof T.componentWillMount=="function"&&T.componentWillMount(),typeof T.UNSAFE_componentWillMount=="function"&&T.UNSAFE_componentWillMount()),typeof T.componentDidMount=="function"&&(i.flags|=4194308)):(typeof T.componentDidMount=="function"&&(i.flags|=4194308),i.memoizedProps=l,i.memoizedState=B),T.props=l,T.state=B,T.context=re,l=N):(typeof T.componentDidMount=="function"&&(i.flags|=4194308),l=!1)}else{T=i.stateNode,ch(t,i),N=i.memoizedProps,re=i.type===i.elementType?N:oi(i.type,N),T.props=re,xe=i.pendingProps,_e=T.context,B=a.contextType,typeof B=="object"&&B!==null?B=$n(B):(B=Rn(a)?Nr:fn.current,B=hs(i,B));var Ie=a.getDerivedStateFromProps;(ve=typeof Ie=="function"||typeof T.getSnapshotBeforeUpdate=="function")||typeof T.UNSAFE_componentWillReceiveProps!="function"&&typeof T.componentWillReceiveProps!="function"||(N!==xe||_e!==B)&&Oh(i,T,l,B),fr=!1,_e=i.memoizedState,T.state=_e,Co(i,l,T,f);var Ve=i.memoizedState;N!==xe||_e!==Ve||Cn.current||fr?(typeof Ie=="function"&&(Gu(i,a,Ie,l),Ve=i.memoizedState),(re=fr||Uh(i,a,re,l,_e,Ve,B)||!1)?(ve||typeof T.UNSAFE_componentWillUpdate!="function"&&typeof T.componentWillUpdate!="function"||(typeof T.componentWillUpdate=="function"&&T.componentWillUpdate(l,Ve,B),typeof T.UNSAFE_componentWillUpdate=="function"&&T.UNSAFE_componentWillUpdate(l,Ve,B)),typeof T.componentDidUpdate=="function"&&(i.flags|=4),typeof T.getSnapshotBeforeUpdate=="function"&&(i.flags|=1024)):(typeof T.componentDidUpdate!="function"||N===t.memoizedProps&&_e===t.memoizedState||(i.flags|=4),typeof T.getSnapshotBeforeUpdate!="function"||N===t.memoizedProps&&_e===t.memoizedState||(i.flags|=1024),i.memoizedProps=l,i.memoizedState=Ve),T.props=l,T.state=Ve,T.context=B,l=re):(typeof T.componentDidUpdate!="function"||N===t.memoizedProps&&_e===t.memoizedState||(i.flags|=4),typeof T.getSnapshotBeforeUpdate!="function"||N===t.memoizedProps&&_e===t.memoizedState||(i.flags|=1024),l=!1)}return qu(t,i,a,l,h,f)}function qu(t,i,a,l,f,h){Yh(t,i);var T=(i.flags&128)!==0;if(!l&&!T)return f&&Jd(i,a,!1),zi(t,i,h);l=i.stateNode,w_.current=i;var N=T&&typeof a.getDerivedStateFromError!="function"?null:l.render();return i.flags|=1,t!==null&&T?(i.child=_s(i,t.child,null,h),i.child=_s(i,null,N,h)):Sn(t,i,N,h),i.memoizedState=l.state,f&&Jd(i,a,!0),i.child}function $h(t){var i=t.stateNode;i.pendingContext?Zd(t,i.pendingContext,i.pendingContext!==i.context):i.context&&Zd(t,i.context,!1),Du(t,i.containerInfo)}function Kh(t,i,a,l,f){return gs(),Tu(f),i.flags|=256,Sn(t,i,a,l),i.child}var $u={dehydrated:null,treeContext:null,retryLane:0};function Ku(t){return{baseLanes:t,cachePool:null,transitions:null}}function Zh(t,i,a){var l=i.pendingProps,f=Vt.current,h=!1,T=(i.flags&128)!==0,N;if((N=T)||(N=t!==null&&t.memoizedState===null?!1:(f&2)!==0),N?(h=!0,i.flags&=-129):(t===null||t.memoizedState!==null)&&(f|=1),Ut(Vt,f&1),t===null)return Eu(i),t=i.memoizedState,t!==null&&(t=t.dehydrated,t!==null)?((i.mode&1)===0?i.lanes=1:t.data==="$!"?i.lanes=8:i.lanes=1073741824,null):(T=l.children,t=l.fallback,h?(l=i.mode,h=i.child,T={mode:"hidden",children:T},(l&1)===0&&h!==null?(h.childLanes=0,h.pendingProps=T):h=qo(T,l,0,null),t=Gr(t,l,a,null),h.return=i,t.return=i,h.sibling=t,i.child=h,i.child.memoizedState=Ku(a),i.memoizedState=$u,t):Zu(i,T));if(f=t.memoizedState,f!==null&&(N=f.dehydrated,N!==null))return A_(t,i,T,l,N,f,a);if(h){h=l.fallback,T=i.mode,f=t.child,N=f.sibling;var B={mode:"hidden",children:l.children};return(T&1)===0&&i.child!==f?(l=i.child,l.childLanes=0,l.pendingProps=B,i.deletions=null):(l=vr(f,B),l.subtreeFlags=f.subtreeFlags&14680064),N!==null?h=vr(N,h):(h=Gr(h,T,a,null),h.flags|=2),h.return=i,l.return=i,l.sibling=h,i.child=l,l=h,h=i.child,T=t.child.memoizedState,T=T===null?Ku(a):{baseLanes:T.baseLanes|a,cachePool:null,transitions:T.transitions},h.memoizedState=T,h.childLanes=t.childLanes&~a,i.memoizedState=$u,l}return h=t.child,t=h.sibling,l=vr(h,{mode:"visible",children:l.children}),(i.mode&1)===0&&(l.lanes=a),l.return=i,l.sibling=null,t!==null&&(a=i.deletions,a===null?(i.deletions=[t],i.flags|=16):a.push(t)),i.child=l,i.memoizedState=null,l}function Zu(t,i){return i=qo({mode:"visible",children:i},t.mode,0,null),i.return=t,t.child=i}function Uo(t,i,a,l){return l!==null&&Tu(l),_s(i,t.child,null,a),t=Zu(i,i.pendingProps.children),t.flags|=2,i.memoizedState=null,t}function A_(t,i,a,l,f,h,T){if(a)return i.flags&256?(i.flags&=-257,l=Xu(Error(n(422))),Uo(t,i,T,l)):i.memoizedState!==null?(i.child=t.child,i.flags|=128,null):(h=l.fallback,f=i.mode,l=qo({mode:"visible",children:l.children},f,0,null),h=Gr(h,f,T,null),h.flags|=2,l.return=i,h.return=i,l.sibling=h,i.child=l,(i.mode&1)!==0&&_s(i,t.child,null,T),i.child.memoizedState=Ku(T),i.memoizedState=$u,h);if((i.mode&1)===0)return Uo(t,i,T,null);if(f.data==="$!"){if(l=f.nextSibling&&f.nextSibling.dataset,l)var N=l.dgst;return l=N,h=Error(n(419)),l=Xu(h,l,void 0),Uo(t,i,T,l)}if(N=(T&t.childLanes)!==0,bn||N){if(l=sn,l!==null){switch(T&-T){case 4:f=2;break;case 16:f=8;break;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:f=32;break;case 536870912:f=268435456;break;default:f=0}f=(f&(l.suspendedLanes|T))!==0?0:f,f!==0&&f!==h.retryLane&&(h.retryLane=f,Bi(t,f),ci(l,t,f,-1))}return hc(),l=Xu(Error(n(421))),Uo(t,i,T,l)}return f.data==="$?"?(i.flags|=128,i.child=t.child,i=k_.bind(null,t),f._reactRetry=i,null):(t=h.treeContext,kn=or(f.nextSibling),Bn=i,zt=!0,ai=null,t!==null&&(Yn[qn++]=Fi,Yn[qn++]=Oi,Yn[qn++]=Ir,Fi=t.id,Oi=t.overflow,Ir=i),i=Zu(i,l.children),i.flags|=4096,i)}function Qh(t,i,a){t.lanes|=i;var l=t.alternate;l!==null&&(l.lanes|=i),Ru(t.return,i,a)}function Qu(t,i,a,l,f){var h=t.memoizedState;h===null?t.memoizedState={isBackwards:i,rendering:null,renderingStartTime:0,last:l,tail:a,tailMode:f}:(h.isBackwards=i,h.rendering=null,h.renderingStartTime=0,h.last=l,h.tail=a,h.tailMode=f)}function Jh(t,i,a){var l=i.pendingProps,f=l.revealOrder,h=l.tail;if(Sn(t,i,l.children,a),l=Vt.current,(l&2)!==0)l=l&1|2,i.flags|=128;else{if(t!==null&&(t.flags&128)!==0)e:for(t=i.child;t!==null;){if(t.tag===13)t.memoizedState!==null&&Qh(t,a,i);else if(t.tag===19)Qh(t,a,i);else if(t.child!==null){t.child.return=t,t=t.child;continue}if(t===i)break e;for(;t.sibling===null;){if(t.return===null||t.return===i)break e;t=t.return}t.sibling.return=t.return,t=t.sibling}l&=1}if(Ut(Vt,l),(i.mode&1)===0)i.memoizedState=null;else switch(f){case"forwards":for(a=i.child,f=null;a!==null;)t=a.alternate,t!==null&&Ro(t)===null&&(f=a),a=a.sibling;a=f,a===null?(f=i.child,i.child=null):(f=a.sibling,a.sibling=null),Qu(i,!1,f,a,h);break;case"backwards":for(a=null,f=i.child,i.child=null;f!==null;){if(t=f.alternate,t!==null&&Ro(t)===null){i.child=f;break}t=f.sibling,f.sibling=a,a=f,f=t}Qu(i,!0,a,null,h);break;case"together":Qu(i,!1,null,null,void 0);break;default:i.memoizedState=null}return i.child}function Fo(t,i){(i.mode&1)===0&&t!==null&&(t.alternate=null,i.alternate=null,i.flags|=2)}function zi(t,i,a){if(t!==null&&(i.dependencies=t.dependencies),kr|=i.lanes,(a&i.childLanes)===0)return null;if(t!==null&&i.child!==t.child)throw Error(n(153));if(i.child!==null){for(t=i.child,a=vr(t,t.pendingProps),i.child=a,a.return=i;t.sibling!==null;)t=t.sibling,a=a.sibling=vr(t,t.pendingProps),a.return=i;a.sibling=null}return i.child}function C_(t,i,a){switch(i.tag){case 3:$h(i),gs();break;case 5:hh(i);break;case 1:Rn(i.type)&&vo(i);break;case 4:Du(i,i.stateNode.containerInfo);break;case 10:var l=i.type._context,f=i.memoizedProps.value;Ut(To,l._currentValue),l._currentValue=f;break;case 13:if(l=i.memoizedState,l!==null)return l.dehydrated!==null?(Ut(Vt,Vt.current&1),i.flags|=128,null):(a&i.child.childLanes)!==0?Zh(t,i,a):(Ut(Vt,Vt.current&1),t=zi(t,i,a),t!==null?t.sibling:null);Ut(Vt,Vt.current&1);break;case 19:if(l=(a&i.childLanes)!==0,(t.flags&128)!==0){if(l)return Jh(t,i,a);i.flags|=128}if(f=i.memoizedState,f!==null&&(f.rendering=null,f.tail=null,f.lastEffect=null),Ut(Vt,Vt.current),l)break;return null;case 22:case 23:return i.lanes=0,jh(t,i,a)}return zi(t,i,a)}var ep,Ju,tp,np;ep=function(t,i){for(var a=i.child;a!==null;){if(a.tag===5||a.tag===6)t.appendChild(a.stateNode);else if(a.tag!==4&&a.child!==null){a.child.return=a,a=a.child;continue}if(a===i)break;for(;a.sibling===null;){if(a.return===null||a.return===i)return;a=a.return}a.sibling.return=a.return,a=a.sibling}},Ju=function(){},tp=function(t,i,a,l){var f=t.memoizedProps;if(f!==l){t=i.stateNode,Or(xi.current);var h=null;switch(a){case"input":f=xt(t,f),l=xt(t,l),h=[];break;case"select":f=le({},f,{value:void 0}),l=le({},l,{value:void 0}),h=[];break;case"textarea":f=Ge(t,f),l=Ge(t,l),h=[];break;default:typeof f.onClick!="function"&&typeof l.onClick=="function"&&(t.onclick=mo)}ke(a,l);var T;a=null;for(re in f)if(!l.hasOwnProperty(re)&&f.hasOwnProperty(re)&&f[re]!=null)if(re==="style"){var N=f[re];for(T in N)N.hasOwnProperty(T)&&(a||(a={}),a[T]="")}else re!=="dangerouslySetInnerHTML"&&re!=="children"&&re!=="suppressContentEditableWarning"&&re!=="suppressHydrationWarning"&&re!=="autoFocus"&&(o.hasOwnProperty(re)?h||(h=[]):(h=h||[]).push(re,null));for(re in l){var B=l[re];if(N=f!=null?f[re]:void 0,l.hasOwnProperty(re)&&B!==N&&(B!=null||N!=null))if(re==="style")if(N){for(T in N)!N.hasOwnProperty(T)||B&&B.hasOwnProperty(T)||(a||(a={}),a[T]="");for(T in B)B.hasOwnProperty(T)&&N[T]!==B[T]&&(a||(a={}),a[T]=B[T])}else a||(h||(h=[]),h.push(re,a)),a=B;else re==="dangerouslySetInnerHTML"?(B=B?B.__html:void 0,N=N?N.__html:void 0,B!=null&&N!==B&&(h=h||[]).push(re,B)):re==="children"?typeof B!="string"&&typeof B!="number"||(h=h||[]).push(re,""+B):re!=="suppressContentEditableWarning"&&re!=="suppressHydrationWarning"&&(o.hasOwnProperty(re)?(B!=null&&re==="onScroll"&&Ot("scroll",t),h||N===B||(h=[])):(h=h||[]).push(re,B))}a&&(h=h||[]).push("style",a);var re=h;(i.updateQueue=re)&&(i.flags|=4)}},np=function(t,i,a,l){a!==l&&(i.flags|=4)};function Ea(t,i){if(!zt)switch(t.tailMode){case"hidden":i=t.tail;for(var a=null;i!==null;)i.alternate!==null&&(a=i),i=i.sibling;a===null?t.tail=null:a.sibling=null;break;case"collapsed":a=t.tail;for(var l=null;a!==null;)a.alternate!==null&&(l=a),a=a.sibling;l===null?i||t.tail===null?t.tail=null:t.tail.sibling=null:l.sibling=null}}function hn(t){var i=t.alternate!==null&&t.alternate.child===t.child,a=0,l=0;if(i)for(var f=t.child;f!==null;)a|=f.lanes|f.childLanes,l|=f.subtreeFlags&14680064,l|=f.flags&14680064,f.return=t,f=f.sibling;else for(f=t.child;f!==null;)a|=f.lanes|f.childLanes,l|=f.subtreeFlags,l|=f.flags,f.return=t,f=f.sibling;return t.subtreeFlags|=l,t.childLanes=a,i}function R_(t,i,a){var l=i.pendingProps;switch(yu(i),i.tag){case 2:case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return hn(i),null;case 1:return Rn(i.type)&&_o(),hn(i),null;case 3:return l=i.stateNode,Ss(),Bt(Cn),Bt(fn),Iu(),l.pendingContext&&(l.context=l.pendingContext,l.pendingContext=null),(t===null||t.child===null)&&(Mo(i)?i.flags|=4:t===null||t.memoizedState.isDehydrated&&(i.flags&256)===0||(i.flags|=1024,ai!==null&&(cc(ai),ai=null))),Ju(t,i),hn(i),null;case 5:Lu(i);var f=Or(va.current);if(a=i.type,t!==null&&i.stateNode!=null)tp(t,i,a,l,f),t.ref!==i.ref&&(i.flags|=512,i.flags|=2097152);else{if(!l){if(i.stateNode===null)throw Error(n(166));return hn(i),null}if(t=Or(xi.current),Mo(i)){l=i.stateNode,a=i.type;var h=i.memoizedProps;switch(l[vi]=i,l[ha]=h,t=(i.mode&1)!==0,a){case"dialog":Ot("cancel",l),Ot("close",l);break;case"iframe":case"object":case"embed":Ot("load",l);break;case"video":case"audio":for(f=0;f<ca.length;f++)Ot(ca[f],l);break;case"source":Ot("error",l);break;case"img":case"image":case"link":Ot("error",l),Ot("load",l);break;case"details":Ot("toggle",l);break;case"input":Ct(l,h),Ot("invalid",l);break;case"select":l._wrapperState={wasMultiple:!!h.multiple},Ot("invalid",l);break;case"textarea":P(l,h),Ot("invalid",l)}ke(a,h),f=null;for(var T in h)if(h.hasOwnProperty(T)){var N=h[T];T==="children"?typeof N=="string"?l.textContent!==N&&(h.suppressHydrationWarning!==!0&&po(l.textContent,N,t),f=["children",N]):typeof N=="number"&&l.textContent!==""+N&&(h.suppressHydrationWarning!==!0&&po(l.textContent,N,t),f=["children",""+N]):o.hasOwnProperty(T)&&N!=null&&T==="onScroll"&&Ot("scroll",l)}switch(a){case"input":nt(l),k(l,h,!0);break;case"textarea":nt(l),G(l);break;case"select":case"option":break;default:typeof h.onClick=="function"&&(l.onclick=mo)}l=f,i.updateQueue=l,l!==null&&(i.flags|=4)}else{T=f.nodeType===9?f:f.ownerDocument,t==="http://www.w3.org/1999/xhtml"&&(t=de(a)),t==="http://www.w3.org/1999/xhtml"?a==="script"?(t=T.createElement("div"),t.innerHTML="<script><\/script>",t=t.removeChild(t.firstChild)):typeof l.is=="string"?t=T.createElement(a,{is:l.is}):(t=T.createElement(a),a==="select"&&(T=t,l.multiple?T.multiple=!0:l.size&&(T.size=l.size))):t=T.createElementNS(t,a),t[vi]=i,t[ha]=l,ep(t,i,!1,!1),i.stateNode=t;e:{switch(T=De(a,l),a){case"dialog":Ot("cancel",t),Ot("close",t),f=l;break;case"iframe":case"object":case"embed":Ot("load",t),f=l;break;case"video":case"audio":for(f=0;f<ca.length;f++)Ot(ca[f],t);f=l;break;case"source":Ot("error",t),f=l;break;case"img":case"image":case"link":Ot("error",t),Ot("load",t),f=l;break;case"details":Ot("toggle",t),f=l;break;case"input":Ct(t,l),f=xt(t,l),Ot("invalid",t);break;case"option":f=l;break;case"select":t._wrapperState={wasMultiple:!!l.multiple},f=le({},l,{value:void 0}),Ot("invalid",t);break;case"textarea":P(t,l),f=Ge(t,l),Ot("invalid",t);break;default:f=l}ke(a,f),N=f;for(h in N)if(N.hasOwnProperty(h)){var B=N[h];h==="style"?Te(t,B):h==="dangerouslySetInnerHTML"?(B=B?B.__html:void 0,B!=null&&Be(t,B)):h==="children"?typeof B=="string"?(a!=="textarea"||B!=="")&&we(t,B):typeof B=="number"&&we(t,""+B):h!=="suppressContentEditableWarning"&&h!=="suppressHydrationWarning"&&h!=="autoFocus"&&(o.hasOwnProperty(h)?B!=null&&h==="onScroll"&&Ot("scroll",t):B!=null&&L(t,h,B,T))}switch(a){case"input":nt(t),k(t,l,!1);break;case"textarea":nt(t),G(t);break;case"option":l.value!=null&&t.setAttribute("value",""+pe(l.value));break;case"select":t.multiple=!!l.multiple,h=l.value,h!=null?St(t,!!l.multiple,h,!1):l.defaultValue!=null&&St(t,!!l.multiple,l.defaultValue,!0);break;default:typeof f.onClick=="function"&&(t.onclick=mo)}switch(a){case"button":case"input":case"select":case"textarea":l=!!l.autoFocus;break e;case"img":l=!0;break e;default:l=!1}}l&&(i.flags|=4)}i.ref!==null&&(i.flags|=512,i.flags|=2097152)}return hn(i),null;case 6:if(t&&i.stateNode!=null)np(t,i,t.memoizedProps,l);else{if(typeof l!="string"&&i.stateNode===null)throw Error(n(166));if(a=Or(va.current),Or(xi.current),Mo(i)){if(l=i.stateNode,a=i.memoizedProps,l[vi]=i,(h=l.nodeValue!==a)&&(t=Bn,t!==null))switch(t.tag){case 3:po(l.nodeValue,a,(t.mode&1)!==0);break;case 5:t.memoizedProps.suppressHydrationWarning!==!0&&po(l.nodeValue,a,(t.mode&1)!==0)}h&&(i.flags|=4)}else l=(a.nodeType===9?a:a.ownerDocument).createTextNode(l),l[vi]=i,i.stateNode=l}return hn(i),null;case 13:if(Bt(Vt),l=i.memoizedState,t===null||t.memoizedState!==null&&t.memoizedState.dehydrated!==null){if(zt&&kn!==null&&(i.mode&1)!==0&&(i.flags&128)===0)sh(),gs(),i.flags|=98560,h=!1;else if(h=Mo(i),l!==null&&l.dehydrated!==null){if(t===null){if(!h)throw Error(n(318));if(h=i.memoizedState,h=h!==null?h.dehydrated:null,!h)throw Error(n(317));h[vi]=i}else gs(),(i.flags&128)===0&&(i.memoizedState=null),i.flags|=4;hn(i),h=!1}else ai!==null&&(cc(ai),ai=null),h=!0;if(!h)return i.flags&65536?i:null}return(i.flags&128)!==0?(i.lanes=a,i):(l=l!==null,l!==(t!==null&&t.memoizedState!==null)&&l&&(i.child.flags|=8192,(i.mode&1)!==0&&(t===null||(Vt.current&1)!==0?en===0&&(en=3):hc())),i.updateQueue!==null&&(i.flags|=4),hn(i),null);case 4:return Ss(),Ju(t,i),t===null&&fa(i.stateNode.containerInfo),hn(i),null;case 10:return Cu(i.type._context),hn(i),null;case 17:return Rn(i.type)&&_o(),hn(i),null;case 19:if(Bt(Vt),h=i.memoizedState,h===null)return hn(i),null;if(l=(i.flags&128)!==0,T=h.rendering,T===null)if(l)Ea(h,!1);else{if(en!==0||t!==null&&(t.flags&128)!==0)for(t=i.child;t!==null;){if(T=Ro(t),T!==null){for(i.flags|=128,Ea(h,!1),l=T.updateQueue,l!==null&&(i.updateQueue=l,i.flags|=4),i.subtreeFlags=0,l=a,a=i.child;a!==null;)h=a,t=l,h.flags&=14680066,T=h.alternate,T===null?(h.childLanes=0,h.lanes=t,h.child=null,h.subtreeFlags=0,h.memoizedProps=null,h.memoizedState=null,h.updateQueue=null,h.dependencies=null,h.stateNode=null):(h.childLanes=T.childLanes,h.lanes=T.lanes,h.child=T.child,h.subtreeFlags=0,h.deletions=null,h.memoizedProps=T.memoizedProps,h.memoizedState=T.memoizedState,h.updateQueue=T.updateQueue,h.type=T.type,t=T.dependencies,h.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext}),a=a.sibling;return Ut(Vt,Vt.current&1|2),i.child}t=t.sibling}h.tail!==null&&w()>Ts&&(i.flags|=128,l=!0,Ea(h,!1),i.lanes=4194304)}else{if(!l)if(t=Ro(T),t!==null){if(i.flags|=128,l=!0,a=t.updateQueue,a!==null&&(i.updateQueue=a,i.flags|=4),Ea(h,!0),h.tail===null&&h.tailMode==="hidden"&&!T.alternate&&!zt)return hn(i),null}else 2*w()-h.renderingStartTime>Ts&&a!==1073741824&&(i.flags|=128,l=!0,Ea(h,!1),i.lanes=4194304);h.isBackwards?(T.sibling=i.child,i.child=T):(a=h.last,a!==null?a.sibling=T:i.child=T,h.last=T)}return h.tail!==null?(i=h.tail,h.rendering=i,h.tail=i.sibling,h.renderingStartTime=w(),i.sibling=null,a=Vt.current,Ut(Vt,l?a&1|2:a&1),i):(hn(i),null);case 22:case 23:return dc(),l=i.memoizedState!==null,t!==null&&t.memoizedState!==null!==l&&(i.flags|=8192),l&&(i.mode&1)!==0?(zn&1073741824)!==0&&(hn(i),i.subtreeFlags&6&&(i.flags|=8192)):hn(i),null;case 24:return null;case 25:return null}throw Error(n(156,i.tag))}function b_(t,i){switch(yu(i),i.tag){case 1:return Rn(i.type)&&_o(),t=i.flags,t&65536?(i.flags=t&-65537|128,i):null;case 3:return Ss(),Bt(Cn),Bt(fn),Iu(),t=i.flags,(t&65536)!==0&&(t&128)===0?(i.flags=t&-65537|128,i):null;case 5:return Lu(i),null;case 13:if(Bt(Vt),t=i.memoizedState,t!==null&&t.dehydrated!==null){if(i.alternate===null)throw Error(n(340));gs()}return t=i.flags,t&65536?(i.flags=t&-65537|128,i):null;case 19:return Bt(Vt),null;case 4:return Ss(),null;case 10:return Cu(i.type._context),null;case 22:case 23:return dc(),null;case 24:return null;default:return null}}var Oo=!1,pn=!1,P_=typeof WeakSet=="function"?WeakSet:Set,Oe=null;function Ms(t,i){var a=t.ref;if(a!==null)if(typeof a=="function")try{a(null)}catch(l){Gt(t,i,l)}else a.current=null}function ec(t,i,a){try{a()}catch(l){Gt(t,i,l)}}var ip=!1;function D_(t,i){if(du=no,t=Ud(),ru(t)){if("selectionStart"in t)var a={start:t.selectionStart,end:t.selectionEnd};else e:{a=(a=t.ownerDocument)&&a.defaultView||window;var l=a.getSelection&&a.getSelection();if(l&&l.rangeCount!==0){a=l.anchorNode;var f=l.anchorOffset,h=l.focusNode;l=l.focusOffset;try{a.nodeType,h.nodeType}catch{a=null;break e}var T=0,N=-1,B=-1,re=0,ve=0,xe=t,_e=null;t:for(;;){for(var Ie;xe!==a||f!==0&&xe.nodeType!==3||(N=T+f),xe!==h||l!==0&&xe.nodeType!==3||(B=T+l),xe.nodeType===3&&(T+=xe.nodeValue.length),(Ie=xe.firstChild)!==null;)_e=xe,xe=Ie;for(;;){if(xe===t)break t;if(_e===a&&++re===f&&(N=T),_e===h&&++ve===l&&(B=T),(Ie=xe.nextSibling)!==null)break;xe=_e,_e=xe.parentNode}xe=Ie}a=N===-1||B===-1?null:{start:N,end:B}}else a=null}a=a||{start:0,end:0}}else a=null;for(hu={focusedElem:t,selectionRange:a},no=!1,Oe=i;Oe!==null;)if(i=Oe,t=i.child,(i.subtreeFlags&1028)!==0&&t!==null)t.return=i,Oe=t;else for(;Oe!==null;){i=Oe;try{var Ve=i.alternate;if((i.flags&1024)!==0)switch(i.tag){case 0:case 11:case 15:break;case 1:if(Ve!==null){var je=Ve.memoizedProps,Yt=Ve.memoizedState,Y=i.stateNode,H=Y.getSnapshotBeforeUpdate(i.elementType===i.type?je:oi(i.type,je),Yt);Y.__reactInternalSnapshotBeforeUpdate=H}break;case 3:var Z=i.stateNode.containerInfo;Z.nodeType===1?Z.textContent="":Z.nodeType===9&&Z.documentElement&&Z.removeChild(Z.documentElement);break;case 5:case 6:case 4:case 17:break;default:throw Error(n(163))}}catch(Ee){Gt(i,i.return,Ee)}if(t=i.sibling,t!==null){t.return=i.return,Oe=t;break}Oe=i.return}return Ve=ip,ip=!1,Ve}function Ta(t,i,a){var l=i.updateQueue;if(l=l!==null?l.lastEffect:null,l!==null){var f=l=l.next;do{if((f.tag&t)===t){var h=f.destroy;f.destroy=void 0,h!==void 0&&ec(i,a,h)}f=f.next}while(f!==l)}}function Bo(t,i){if(i=i.updateQueue,i=i!==null?i.lastEffect:null,i!==null){var a=i=i.next;do{if((a.tag&t)===t){var l=a.create;a.destroy=l()}a=a.next}while(a!==i)}}function tc(t){var i=t.ref;if(i!==null){var a=t.stateNode;switch(t.tag){case 5:t=a;break;default:t=a}typeof i=="function"?i(t):i.current=t}}function rp(t){var i=t.alternate;i!==null&&(t.alternate=null,rp(i)),t.child=null,t.deletions=null,t.sibling=null,t.tag===5&&(i=t.stateNode,i!==null&&(delete i[vi],delete i[ha],delete i[_u],delete i[h_],delete i[p_])),t.stateNode=null,t.return=null,t.dependencies=null,t.memoizedProps=null,t.memoizedState=null,t.pendingProps=null,t.stateNode=null,t.updateQueue=null}function sp(t){return t.tag===5||t.tag===3||t.tag===4}function ap(t){e:for(;;){for(;t.sibling===null;){if(t.return===null||sp(t.return))return null;t=t.return}for(t.sibling.return=t.return,t=t.sibling;t.tag!==5&&t.tag!==6&&t.tag!==18;){if(t.flags&2||t.child===null||t.tag===4)continue e;t.child.return=t,t=t.child}if(!(t.flags&2))return t.stateNode}}function nc(t,i,a){var l=t.tag;if(l===5||l===6)t=t.stateNode,i?a.nodeType===8?a.parentNode.insertBefore(t,i):a.insertBefore(t,i):(a.nodeType===8?(i=a.parentNode,i.insertBefore(t,a)):(i=a,i.appendChild(t)),a=a._reactRootContainer,a!=null||i.onclick!==null||(i.onclick=mo));else if(l!==4&&(t=t.child,t!==null))for(nc(t,i,a),t=t.sibling;t!==null;)nc(t,i,a),t=t.sibling}function ic(t,i,a){var l=t.tag;if(l===5||l===6)t=t.stateNode,i?a.insertBefore(t,i):a.appendChild(t);else if(l!==4&&(t=t.child,t!==null))for(ic(t,i,a),t=t.sibling;t!==null;)ic(t,i,a),t=t.sibling}var ln=null,li=!1;function hr(t,i,a){for(a=a.child;a!==null;)op(t,i,a),a=a.sibling}function op(t,i,a){if(Ne&&typeof Ne.onCommitFiberUnmount=="function")try{Ne.onCommitFiberUnmount(Re,a)}catch{}switch(a.tag){case 5:pn||Ms(a,i);case 6:var l=ln,f=li;ln=null,hr(t,i,a),ln=l,li=f,ln!==null&&(li?(t=ln,a=a.stateNode,t.nodeType===8?t.parentNode.removeChild(a):t.removeChild(a)):ln.removeChild(a.stateNode));break;case 18:ln!==null&&(li?(t=ln,a=a.stateNode,t.nodeType===8?gu(t.parentNode,a):t.nodeType===1&&gu(t,a),na(t)):gu(ln,a.stateNode));break;case 4:l=ln,f=li,ln=a.stateNode.containerInfo,li=!0,hr(t,i,a),ln=l,li=f;break;case 0:case 11:case 14:case 15:if(!pn&&(l=a.updateQueue,l!==null&&(l=l.lastEffect,l!==null))){f=l=l.next;do{var h=f,T=h.destroy;h=h.tag,T!==void 0&&((h&2)!==0||(h&4)!==0)&&ec(a,i,T),f=f.next}while(f!==l)}hr(t,i,a);break;case 1:if(!pn&&(Ms(a,i),l=a.stateNode,typeof l.componentWillUnmount=="function"))try{l.props=a.memoizedProps,l.state=a.memoizedState,l.componentWillUnmount()}catch(N){Gt(a,i,N)}hr(t,i,a);break;case 21:hr(t,i,a);break;case 22:a.mode&1?(pn=(l=pn)||a.memoizedState!==null,hr(t,i,a),pn=l):hr(t,i,a);break;default:hr(t,i,a)}}function lp(t){var i=t.updateQueue;if(i!==null){t.updateQueue=null;var a=t.stateNode;a===null&&(a=t.stateNode=new P_),i.forEach(function(l){var f=z_.bind(null,t,l);a.has(l)||(a.add(l),l.then(f,f))})}}function ui(t,i){var a=i.deletions;if(a!==null)for(var l=0;l<a.length;l++){var f=a[l];try{var h=t,T=i,N=T;e:for(;N!==null;){switch(N.tag){case 5:ln=N.stateNode,li=!1;break e;case 3:ln=N.stateNode.containerInfo,li=!0;break e;case 4:ln=N.stateNode.containerInfo,li=!0;break e}N=N.return}if(ln===null)throw Error(n(160));op(h,T,f),ln=null,li=!1;var B=f.alternate;B!==null&&(B.return=null),f.return=null}catch(re){Gt(f,i,re)}}if(i.subtreeFlags&12854)for(i=i.child;i!==null;)up(i,t),i=i.sibling}function up(t,i){var a=t.alternate,l=t.flags;switch(t.tag){case 0:case 11:case 14:case 15:if(ui(i,t),yi(t),l&4){try{Ta(3,t,t.return),Bo(3,t)}catch(je){Gt(t,t.return,je)}try{Ta(5,t,t.return)}catch(je){Gt(t,t.return,je)}}break;case 1:ui(i,t),yi(t),l&512&&a!==null&&Ms(a,a.return);break;case 5:if(ui(i,t),yi(t),l&512&&a!==null&&Ms(a,a.return),t.flags&32){var f=t.stateNode;try{we(f,"")}catch(je){Gt(t,t.return,je)}}if(l&4&&(f=t.stateNode,f!=null)){var h=t.memoizedProps,T=a!==null?a.memoizedProps:h,N=t.type,B=t.updateQueue;if(t.updateQueue=null,B!==null)try{N==="input"&&h.type==="radio"&&h.name!=null&&ut(f,h),De(N,T);var re=De(N,h);for(T=0;T<B.length;T+=2){var ve=B[T],xe=B[T+1];ve==="style"?Te(f,xe):ve==="dangerouslySetInnerHTML"?Be(f,xe):ve==="children"?we(f,xe):L(f,ve,xe,re)}switch(N){case"input":Ft(f,h);break;case"textarea":E(f,h);break;case"select":var _e=f._wrapperState.wasMultiple;f._wrapperState.wasMultiple=!!h.multiple;var Ie=h.value;Ie!=null?St(f,!!h.multiple,Ie,!1):_e!==!!h.multiple&&(h.defaultValue!=null?St(f,!!h.multiple,h.defaultValue,!0):St(f,!!h.multiple,h.multiple?[]:"",!1))}f[ha]=h}catch(je){Gt(t,t.return,je)}}break;case 6:if(ui(i,t),yi(t),l&4){if(t.stateNode===null)throw Error(n(162));f=t.stateNode,h=t.memoizedProps;try{f.nodeValue=h}catch(je){Gt(t,t.return,je)}}break;case 3:if(ui(i,t),yi(t),l&4&&a!==null&&a.memoizedState.isDehydrated)try{na(i.containerInfo)}catch(je){Gt(t,t.return,je)}break;case 4:ui(i,t),yi(t);break;case 13:ui(i,t),yi(t),f=t.child,f.flags&8192&&(h=f.memoizedState!==null,f.stateNode.isHidden=h,!h||f.alternate!==null&&f.alternate.memoizedState!==null||(ac=w())),l&4&&lp(t);break;case 22:if(ve=a!==null&&a.memoizedState!==null,t.mode&1?(pn=(re=pn)||ve,ui(i,t),pn=re):ui(i,t),yi(t),l&8192){if(re=t.memoizedState!==null,(t.stateNode.isHidden=re)&&!ve&&(t.mode&1)!==0)for(Oe=t,ve=t.child;ve!==null;){for(xe=Oe=ve;Oe!==null;){switch(_e=Oe,Ie=_e.child,_e.tag){case 0:case 11:case 14:case 15:Ta(4,_e,_e.return);break;case 1:Ms(_e,_e.return);var Ve=_e.stateNode;if(typeof Ve.componentWillUnmount=="function"){l=_e,a=_e.return;try{i=l,Ve.props=i.memoizedProps,Ve.state=i.memoizedState,Ve.componentWillUnmount()}catch(je){Gt(l,a,je)}}break;case 5:Ms(_e,_e.return);break;case 22:if(_e.memoizedState!==null){dp(xe);continue}}Ie!==null?(Ie.return=_e,Oe=Ie):dp(xe)}ve=ve.sibling}e:for(ve=null,xe=t;;){if(xe.tag===5){if(ve===null){ve=xe;try{f=xe.stateNode,re?(h=f.style,typeof h.setProperty=="function"?h.setProperty("display","none","important"):h.display="none"):(N=xe.stateNode,B=xe.memoizedProps.style,T=B!=null&&B.hasOwnProperty("display")?B.display:null,N.style.display=Se("display",T))}catch(je){Gt(t,t.return,je)}}}else if(xe.tag===6){if(ve===null)try{xe.stateNode.nodeValue=re?"":xe.memoizedProps}catch(je){Gt(t,t.return,je)}}else if((xe.tag!==22&&xe.tag!==23||xe.memoizedState===null||xe===t)&&xe.child!==null){xe.child.return=xe,xe=xe.child;continue}if(xe===t)break e;for(;xe.sibling===null;){if(xe.return===null||xe.return===t)break e;ve===xe&&(ve=null),xe=xe.return}ve===xe&&(ve=null),xe.sibling.return=xe.return,xe=xe.sibling}}break;case 19:ui(i,t),yi(t),l&4&&lp(t);break;case 21:break;default:ui(i,t),yi(t)}}function yi(t){var i=t.flags;if(i&2){try{e:{for(var a=t.return;a!==null;){if(sp(a)){var l=a;break e}a=a.return}throw Error(n(160))}switch(l.tag){case 5:var f=l.stateNode;l.flags&32&&(we(f,""),l.flags&=-33);var h=ap(t);ic(t,h,f);break;case 3:case 4:var T=l.stateNode.containerInfo,N=ap(t);nc(t,N,T);break;default:throw Error(n(161))}}catch(B){Gt(t,t.return,B)}t.flags&=-3}i&4096&&(t.flags&=-4097)}function L_(t,i,a){Oe=t,cp(t)}function cp(t,i,a){for(var l=(t.mode&1)!==0;Oe!==null;){var f=Oe,h=f.child;if(f.tag===22&&l){var T=f.memoizedState!==null||Oo;if(!T){var N=f.alternate,B=N!==null&&N.memoizedState!==null||pn;N=Oo;var re=pn;if(Oo=T,(pn=B)&&!re)for(Oe=f;Oe!==null;)T=Oe,B=T.child,T.tag===22&&T.memoizedState!==null?hp(f):B!==null?(B.return=T,Oe=B):hp(f);for(;h!==null;)Oe=h,cp(h),h=h.sibling;Oe=f,Oo=N,pn=re}fp(t)}else(f.subtreeFlags&8772)!==0&&h!==null?(h.return=f,Oe=h):fp(t)}}function fp(t){for(;Oe!==null;){var i=Oe;if((i.flags&8772)!==0){var a=i.alternate;try{if((i.flags&8772)!==0)switch(i.tag){case 0:case 11:case 15:pn||Bo(5,i);break;case 1:var l=i.stateNode;if(i.flags&4&&!pn)if(a===null)l.componentDidMount();else{var f=i.elementType===i.type?a.memoizedProps:oi(i.type,a.memoizedProps);l.componentDidUpdate(f,a.memoizedState,l.__reactInternalSnapshotBeforeUpdate)}var h=i.updateQueue;h!==null&&dh(i,h,l);break;case 3:var T=i.updateQueue;if(T!==null){if(a=null,i.child!==null)switch(i.child.tag){case 5:a=i.child.stateNode;break;case 1:a=i.child.stateNode}dh(i,T,a)}break;case 5:var N=i.stateNode;if(a===null&&i.flags&4){a=N;var B=i.memoizedProps;switch(i.type){case"button":case"input":case"select":case"textarea":B.autoFocus&&a.focus();break;case"img":B.src&&(a.src=B.src)}}break;case 6:break;case 4:break;case 12:break;case 13:if(i.memoizedState===null){var re=i.alternate;if(re!==null){var ve=re.memoizedState;if(ve!==null){var xe=ve.dehydrated;xe!==null&&na(xe)}}}break;case 19:case 17:case 21:case 22:case 23:case 25:break;default:throw Error(n(163))}pn||i.flags&512&&tc(i)}catch(_e){Gt(i,i.return,_e)}}if(i===t){Oe=null;break}if(a=i.sibling,a!==null){a.return=i.return,Oe=a;break}Oe=i.return}}function dp(t){for(;Oe!==null;){var i=Oe;if(i===t){Oe=null;break}var a=i.sibling;if(a!==null){a.return=i.return,Oe=a;break}Oe=i.return}}function hp(t){for(;Oe!==null;){var i=Oe;try{switch(i.tag){case 0:case 11:case 15:var a=i.return;try{Bo(4,i)}catch(B){Gt(i,a,B)}break;case 1:var l=i.stateNode;if(typeof l.componentDidMount=="function"){var f=i.return;try{l.componentDidMount()}catch(B){Gt(i,f,B)}}var h=i.return;try{tc(i)}catch(B){Gt(i,h,B)}break;case 5:var T=i.return;try{tc(i)}catch(B){Gt(i,T,B)}}}catch(B){Gt(i,i.return,B)}if(i===t){Oe=null;break}var N=i.sibling;if(N!==null){N.return=i.return,Oe=N;break}Oe=i.return}}var N_=Math.ceil,ko=b.ReactCurrentDispatcher,rc=b.ReactCurrentOwner,Zn=b.ReactCurrentBatchConfig,Mt=0,sn=null,Kt=null,un=0,zn=0,Es=lr(0),en=0,wa=null,kr=0,zo=0,sc=0,Aa=null,Pn=null,ac=0,Ts=1/0,Vi=null,Vo=!1,oc=null,pr=null,Ho=!1,mr=null,Go=0,Ca=0,lc=null,Wo=-1,Xo=0;function yn(){return(Mt&6)!==0?w():Wo!==-1?Wo:Wo=w()}function gr(t){return(t.mode&1)===0?1:(Mt&2)!==0&&un!==0?un&-un:g_.transition!==null?(Xo===0&&(Xo=wn()),Xo):(t=st,t!==0||(t=window.event,t=t===void 0?16:md(t.type)),t)}function ci(t,i,a,l){if(50<Ca)throw Ca=0,lc=null,Error(n(185));Fn(t,a,l),((Mt&2)===0||t!==sn)&&(t===sn&&((Mt&2)===0&&(zo|=a),en===4&&_r(t,un)),Dn(t,l),a===1&&Mt===0&&(i.mode&1)===0&&(Ts=w()+500,xo&&cr()))}function Dn(t,i){var a=t.callbackNode;xn(t,i);var l=Xt(t,t===sn?un:0);if(l===0)a!==null&&Ja(a),t.callbackNode=null,t.callbackPriority=0;else if(i=l&-l,t.callbackPriority!==i){if(a!=null&&Ja(a),i===1)t.tag===0?m_(mp.bind(null,t)):eh(mp.bind(null,t)),f_(function(){(Mt&6)===0&&cr()}),a=null;else{switch(ri(l)){case 1:a=se;break;case 4:a=J;break;case 16:a=$;break;case 536870912:a=Ue;break;default:a=$}a=Ep(a,pp.bind(null,t))}t.callbackPriority=i,t.callbackNode=a}}function pp(t,i){if(Wo=-1,Xo=0,(Mt&6)!==0)throw Error(n(327));var a=t.callbackNode;if(ws()&&t.callbackNode!==a)return null;var l=Xt(t,t===sn?un:0);if(l===0)return null;if((l&30)!==0||(l&t.expiredLanes)!==0||i)i=jo(t,l);else{i=l;var f=Mt;Mt|=2;var h=_p();(sn!==t||un!==i)&&(Vi=null,Ts=w()+500,Vr(t,i));do try{F_();break}catch(N){gp(t,N)}while(!0);Au(),ko.current=h,Mt=f,Kt!==null?i=0:(sn=null,un=0,i=en)}if(i!==0){if(i===2&&(f=gt(t),f!==0&&(l=f,i=uc(t,f))),i===1)throw a=wa,Vr(t,0),_r(t,l),Dn(t,w()),a;if(i===6)_r(t,l);else{if(f=t.current.alternate,(l&30)===0&&!I_(f)&&(i=jo(t,l),i===2&&(h=gt(t),h!==0&&(l=h,i=uc(t,h))),i===1))throw a=wa,Vr(t,0),_r(t,l),Dn(t,w()),a;switch(t.finishedWork=f,t.finishedLanes=l,i){case 0:case 1:throw Error(n(345));case 2:Hr(t,Pn,Vi);break;case 3:if(_r(t,l),(l&130023424)===l&&(i=ac+500-w(),10<i)){if(Xt(t,0)!==0)break;if(f=t.suspendedLanes,(f&l)!==l){yn(),t.pingedLanes|=t.suspendedLanes&f;break}t.timeoutHandle=mu(Hr.bind(null,t,Pn,Vi),i);break}Hr(t,Pn,Vi);break;case 4:if(_r(t,l),(l&4194240)===l)break;for(i=t.eventTimes,f=-1;0<l;){var T=31-Je(l);h=1<<T,T=i[T],T>f&&(f=T),l&=~h}if(l=f,l=w()-l,l=(120>l?120:480>l?480:1080>l?1080:1920>l?1920:3e3>l?3e3:4320>l?4320:1960*N_(l/1960))-l,10<l){t.timeoutHandle=mu(Hr.bind(null,t,Pn,Vi),l);break}Hr(t,Pn,Vi);break;case 5:Hr(t,Pn,Vi);break;default:throw Error(n(329))}}}return Dn(t,w()),t.callbackNode===a?pp.bind(null,t):null}function uc(t,i){var a=Aa;return t.current.memoizedState.isDehydrated&&(Vr(t,i).flags|=256),t=jo(t,i),t!==2&&(i=Pn,Pn=a,i!==null&&cc(i)),t}function cc(t){Pn===null?Pn=t:Pn.push.apply(Pn,t)}function I_(t){for(var i=t;;){if(i.flags&16384){var a=i.updateQueue;if(a!==null&&(a=a.stores,a!==null))for(var l=0;l<a.length;l++){var f=a[l],h=f.getSnapshot;f=f.value;try{if(!si(h(),f))return!1}catch{return!1}}}if(a=i.child,i.subtreeFlags&16384&&a!==null)a.return=i,i=a;else{if(i===t)break;for(;i.sibling===null;){if(i.return===null||i.return===t)return!0;i=i.return}i.sibling.return=i.return,i=i.sibling}}return!0}function _r(t,i){for(i&=~sc,i&=~zo,t.suspendedLanes|=i,t.pingedLanes&=~i,t=t.expirationTimes;0<i;){var a=31-Je(i),l=1<<a;t[a]=-1,i&=~l}}function mp(t){if((Mt&6)!==0)throw Error(n(327));ws();var i=Xt(t,0);if((i&1)===0)return Dn(t,w()),null;var a=jo(t,i);if(t.tag!==0&&a===2){var l=gt(t);l!==0&&(i=l,a=uc(t,l))}if(a===1)throw a=wa,Vr(t,0),_r(t,i),Dn(t,w()),a;if(a===6)throw Error(n(345));return t.finishedWork=t.current.alternate,t.finishedLanes=i,Hr(t,Pn,Vi),Dn(t,w()),null}function fc(t,i){var a=Mt;Mt|=1;try{return t(i)}finally{Mt=a,Mt===0&&(Ts=w()+500,xo&&cr())}}function zr(t){mr!==null&&mr.tag===0&&(Mt&6)===0&&ws();var i=Mt;Mt|=1;var a=Zn.transition,l=st;try{if(Zn.transition=null,st=1,t)return t()}finally{st=l,Zn.transition=a,Mt=i,(Mt&6)===0&&cr()}}function dc(){zn=Es.current,Bt(Es)}function Vr(t,i){t.finishedWork=null,t.finishedLanes=0;var a=t.timeoutHandle;if(a!==-1&&(t.timeoutHandle=-1,c_(a)),Kt!==null)for(a=Kt.return;a!==null;){var l=a;switch(yu(l),l.tag){case 1:l=l.type.childContextTypes,l!=null&&_o();break;case 3:Ss(),Bt(Cn),Bt(fn),Iu();break;case 5:Lu(l);break;case 4:Ss();break;case 13:Bt(Vt);break;case 19:Bt(Vt);break;case 10:Cu(l.type._context);break;case 22:case 23:dc()}a=a.return}if(sn=t,Kt=t=vr(t.current,null),un=zn=i,en=0,wa=null,sc=zo=kr=0,Pn=Aa=null,Fr!==null){for(i=0;i<Fr.length;i++)if(a=Fr[i],l=a.interleaved,l!==null){a.interleaved=null;var f=l.next,h=a.pending;if(h!==null){var T=h.next;h.next=f,l.next=T}a.pending=l}Fr=null}return t}function gp(t,i){do{var a=Kt;try{if(Au(),bo.current=No,Po){for(var l=Ht.memoizedState;l!==null;){var f=l.queue;f!==null&&(f.pending=null),l=l.next}Po=!1}if(Br=0,rn=Jt=Ht=null,xa=!1,Sa=0,rc.current=null,a===null||a.return===null){en=1,wa=i,Kt=null;break}e:{var h=t,T=a.return,N=a,B=i;if(i=un,N.flags|=32768,B!==null&&typeof B=="object"&&typeof B.then=="function"){var re=B,ve=N,xe=ve.tag;if((ve.mode&1)===0&&(xe===0||xe===11||xe===15)){var _e=ve.alternate;_e?(ve.updateQueue=_e.updateQueue,ve.memoizedState=_e.memoizedState,ve.lanes=_e.lanes):(ve.updateQueue=null,ve.memoizedState=null)}var Ie=Vh(T);if(Ie!==null){Ie.flags&=-257,Hh(Ie,T,N,h,i),Ie.mode&1&&zh(h,re,i),i=Ie,B=re;var Ve=i.updateQueue;if(Ve===null){var je=new Set;je.add(B),i.updateQueue=je}else Ve.add(B);break e}else{if((i&1)===0){zh(h,re,i),hc();break e}B=Error(n(426))}}else if(zt&&N.mode&1){var Yt=Vh(T);if(Yt!==null){(Yt.flags&65536)===0&&(Yt.flags|=256),Hh(Yt,T,N,h,i),Tu(ys(B,N));break e}}h=B=ys(B,N),en!==4&&(en=2),Aa===null?Aa=[h]:Aa.push(h),h=T;do{switch(h.tag){case 3:h.flags|=65536,i&=-i,h.lanes|=i;var Y=Bh(h,B,i);fh(h,Y);break e;case 1:N=B;var H=h.type,Z=h.stateNode;if((h.flags&128)===0&&(typeof H.getDerivedStateFromError=="function"||Z!==null&&typeof Z.componentDidCatch=="function"&&(pr===null||!pr.has(Z)))){h.flags|=65536,i&=-i,h.lanes|=i;var Ee=kh(h,N,i);fh(h,Ee);break e}}h=h.return}while(h!==null)}xp(a)}catch($e){i=$e,Kt===a&&a!==null&&(Kt=a=a.return);continue}break}while(!0)}function _p(){var t=ko.current;return ko.current=No,t===null?No:t}function hc(){(en===0||en===3||en===2)&&(en=4),sn===null||(kr&268435455)===0&&(zo&268435455)===0||_r(sn,un)}function jo(t,i){var a=Mt;Mt|=2;var l=_p();(sn!==t||un!==i)&&(Vi=null,Vr(t,i));do try{U_();break}catch(f){gp(t,f)}while(!0);if(Au(),Mt=a,ko.current=l,Kt!==null)throw Error(n(261));return sn=null,un=0,en}function U_(){for(;Kt!==null;)vp(Kt)}function F_(){for(;Kt!==null&&!Wl();)vp(Kt)}function vp(t){var i=Mp(t.alternate,t,zn);t.memoizedProps=t.pendingProps,i===null?xp(t):Kt=i,rc.current=null}function xp(t){var i=t;do{var a=i.alternate;if(t=i.return,(i.flags&32768)===0){if(a=R_(a,i,zn),a!==null){Kt=a;return}}else{if(a=b_(a,i),a!==null){a.flags&=32767,Kt=a;return}if(t!==null)t.flags|=32768,t.subtreeFlags=0,t.deletions=null;else{en=6,Kt=null;return}}if(i=i.sibling,i!==null){Kt=i;return}Kt=i=t}while(i!==null);en===0&&(en=5)}function Hr(t,i,a){var l=st,f=Zn.transition;try{Zn.transition=null,st=1,O_(t,i,a,l)}finally{Zn.transition=f,st=l}return null}function O_(t,i,a,l){do ws();while(mr!==null);if((Mt&6)!==0)throw Error(n(327));a=t.finishedWork;var f=t.finishedLanes;if(a===null)return null;if(t.finishedWork=null,t.finishedLanes=0,a===t.current)throw Error(n(177));t.callbackNode=null,t.callbackPriority=0;var h=a.lanes|a.childLanes;if(er(t,h),t===sn&&(Kt=sn=null,un=0),(a.subtreeFlags&2064)===0&&(a.flags&2064)===0||Ho||(Ho=!0,Ep($,function(){return ws(),null})),h=(a.flags&15990)!==0,(a.subtreeFlags&15990)!==0||h){h=Zn.transition,Zn.transition=null;var T=st;st=1;var N=Mt;Mt|=4,rc.current=null,D_(t,a),up(a,t),i_(hu),no=!!du,hu=du=null,t.current=a,L_(a),Xl(),Mt=N,st=T,Zn.transition=h}else t.current=a;if(Ho&&(Ho=!1,mr=t,Go=f),h=t.pendingLanes,h===0&&(pr=null),Ke(a.stateNode),Dn(t,w()),i!==null)for(l=t.onRecoverableError,a=0;a<i.length;a++)f=i[a],l(f.value,{componentStack:f.stack,digest:f.digest});if(Vo)throw Vo=!1,t=oc,oc=null,t;return(Go&1)!==0&&t.tag!==0&&ws(),h=t.pendingLanes,(h&1)!==0?t===lc?Ca++:(Ca=0,lc=t):Ca=0,cr(),null}function ws(){if(mr!==null){var t=ri(Go),i=Zn.transition,a=st;try{if(Zn.transition=null,st=16>t?16:t,mr===null)var l=!1;else{if(t=mr,mr=null,Go=0,(Mt&6)!==0)throw Error(n(331));var f=Mt;for(Mt|=4,Oe=t.current;Oe!==null;){var h=Oe,T=h.child;if((Oe.flags&16)!==0){var N=h.deletions;if(N!==null){for(var B=0;B<N.length;B++){var re=N[B];for(Oe=re;Oe!==null;){var ve=Oe;switch(ve.tag){case 0:case 11:case 15:Ta(8,ve,h)}var xe=ve.child;if(xe!==null)xe.return=ve,Oe=xe;else for(;Oe!==null;){ve=Oe;var _e=ve.sibling,Ie=ve.return;if(rp(ve),ve===re){Oe=null;break}if(_e!==null){_e.return=Ie,Oe=_e;break}Oe=Ie}}}var Ve=h.alternate;if(Ve!==null){var je=Ve.child;if(je!==null){Ve.child=null;do{var Yt=je.sibling;je.sibling=null,je=Yt}while(je!==null)}}Oe=h}}if((h.subtreeFlags&2064)!==0&&T!==null)T.return=h,Oe=T;else e:for(;Oe!==null;){if(h=Oe,(h.flags&2048)!==0)switch(h.tag){case 0:case 11:case 15:Ta(9,h,h.return)}var Y=h.sibling;if(Y!==null){Y.return=h.return,Oe=Y;break e}Oe=h.return}}var H=t.current;for(Oe=H;Oe!==null;){T=Oe;var Z=T.child;if((T.subtreeFlags&2064)!==0&&Z!==null)Z.return=T,Oe=Z;else e:for(T=H;Oe!==null;){if(N=Oe,(N.flags&2048)!==0)try{switch(N.tag){case 0:case 11:case 15:Bo(9,N)}}catch($e){Gt(N,N.return,$e)}if(N===T){Oe=null;break e}var Ee=N.sibling;if(Ee!==null){Ee.return=N.return,Oe=Ee;break e}Oe=N.return}}if(Mt=f,cr(),Ne&&typeof Ne.onPostCommitFiberRoot=="function")try{Ne.onPostCommitFiberRoot(Re,t)}catch{}l=!0}return l}finally{st=a,Zn.transition=i}}return!1}function Sp(t,i,a){i=ys(a,i),i=Bh(t,i,1),t=dr(t,i,1),i=yn(),t!==null&&(Fn(t,1,i),Dn(t,i))}function Gt(t,i,a){if(t.tag===3)Sp(t,t,a);else for(;i!==null;){if(i.tag===3){Sp(i,t,a);break}else if(i.tag===1){var l=i.stateNode;if(typeof i.type.getDerivedStateFromError=="function"||typeof l.componentDidCatch=="function"&&(pr===null||!pr.has(l))){t=ys(a,t),t=kh(i,t,1),i=dr(i,t,1),t=yn(),i!==null&&(Fn(i,1,t),Dn(i,t));break}}i=i.return}}function B_(t,i,a){var l=t.pingCache;l!==null&&l.delete(i),i=yn(),t.pingedLanes|=t.suspendedLanes&a,sn===t&&(un&a)===a&&(en===4||en===3&&(un&130023424)===un&&500>w()-ac?Vr(t,0):sc|=a),Dn(t,i)}function yp(t,i){i===0&&((t.mode&1)===0?i=1:(i=Nt,Nt<<=1,(Nt&130023424)===0&&(Nt=4194304)));var a=yn();t=Bi(t,i),t!==null&&(Fn(t,i,a),Dn(t,a))}function k_(t){var i=t.memoizedState,a=0;i!==null&&(a=i.retryLane),yp(t,a)}function z_(t,i){var a=0;switch(t.tag){case 13:var l=t.stateNode,f=t.memoizedState;f!==null&&(a=f.retryLane);break;case 19:l=t.stateNode;break;default:throw Error(n(314))}l!==null&&l.delete(i),yp(t,a)}var Mp;Mp=function(t,i,a){if(t!==null)if(t.memoizedProps!==i.pendingProps||Cn.current)bn=!0;else{if((t.lanes&a)===0&&(i.flags&128)===0)return bn=!1,C_(t,i,a);bn=(t.flags&131072)!==0}else bn=!1,zt&&(i.flags&1048576)!==0&&th(i,yo,i.index);switch(i.lanes=0,i.tag){case 2:var l=i.type;Fo(t,i),t=i.pendingProps;var f=hs(i,fn.current);xs(i,a),f=Ou(null,i,l,t,f,a);var h=Bu();return i.flags|=1,typeof f=="object"&&f!==null&&typeof f.render=="function"&&f.$$typeof===void 0?(i.tag=1,i.memoizedState=null,i.updateQueue=null,Rn(l)?(h=!0,vo(i)):h=!1,i.memoizedState=f.state!==null&&f.state!==void 0?f.state:null,Pu(i),f.updater=Io,i.stateNode=f,f._reactInternals=i,Wu(i,l,t,a),i=qu(null,i,l,!0,h,a)):(i.tag=0,zt&&h&&Su(i),Sn(null,i,f,a),i=i.child),i;case 16:l=i.elementType;e:{switch(Fo(t,i),t=i.pendingProps,f=l._init,l=f(l._payload),i.type=l,f=i.tag=H_(l),t=oi(l,t),f){case 0:i=Yu(null,i,l,t,a);break e;case 1:i=qh(null,i,l,t,a);break e;case 11:i=Gh(null,i,l,t,a);break e;case 14:i=Wh(null,i,l,oi(l.type,t),a);break e}throw Error(n(306,l,""))}return i;case 0:return l=i.type,f=i.pendingProps,f=i.elementType===l?f:oi(l,f),Yu(t,i,l,f,a);case 1:return l=i.type,f=i.pendingProps,f=i.elementType===l?f:oi(l,f),qh(t,i,l,f,a);case 3:e:{if($h(i),t===null)throw Error(n(387));l=i.pendingProps,h=i.memoizedState,f=h.element,ch(t,i),Co(i,l,null,a);var T=i.memoizedState;if(l=T.element,h.isDehydrated)if(h={element:l,isDehydrated:!1,cache:T.cache,pendingSuspenseBoundaries:T.pendingSuspenseBoundaries,transitions:T.transitions},i.updateQueue.baseState=h,i.memoizedState=h,i.flags&256){f=ys(Error(n(423)),i),i=Kh(t,i,l,a,f);break e}else if(l!==f){f=ys(Error(n(424)),i),i=Kh(t,i,l,a,f);break e}else for(kn=or(i.stateNode.containerInfo.firstChild),Bn=i,zt=!0,ai=null,a=lh(i,null,l,a),i.child=a;a;)a.flags=a.flags&-3|4096,a=a.sibling;else{if(gs(),l===f){i=zi(t,i,a);break e}Sn(t,i,l,a)}i=i.child}return i;case 5:return hh(i),t===null&&Eu(i),l=i.type,f=i.pendingProps,h=t!==null?t.memoizedProps:null,T=f.children,pu(l,f)?T=null:h!==null&&pu(l,h)&&(i.flags|=32),Yh(t,i),Sn(t,i,T,a),i.child;case 6:return t===null&&Eu(i),null;case 13:return Zh(t,i,a);case 4:return Du(i,i.stateNode.containerInfo),l=i.pendingProps,t===null?i.child=_s(i,null,l,a):Sn(t,i,l,a),i.child;case 11:return l=i.type,f=i.pendingProps,f=i.elementType===l?f:oi(l,f),Gh(t,i,l,f,a);case 7:return Sn(t,i,i.pendingProps,a),i.child;case 8:return Sn(t,i,i.pendingProps.children,a),i.child;case 12:return Sn(t,i,i.pendingProps.children,a),i.child;case 10:e:{if(l=i.type._context,f=i.pendingProps,h=i.memoizedProps,T=f.value,Ut(To,l._currentValue),l._currentValue=T,h!==null)if(si(h.value,T)){if(h.children===f.children&&!Cn.current){i=zi(t,i,a);break e}}else for(h=i.child,h!==null&&(h.return=i);h!==null;){var N=h.dependencies;if(N!==null){T=h.child;for(var B=N.firstContext;B!==null;){if(B.context===l){if(h.tag===1){B=ki(-1,a&-a),B.tag=2;var re=h.updateQueue;if(re!==null){re=re.shared;var ve=re.pending;ve===null?B.next=B:(B.next=ve.next,ve.next=B),re.pending=B}}h.lanes|=a,B=h.alternate,B!==null&&(B.lanes|=a),Ru(h.return,a,i),N.lanes|=a;break}B=B.next}}else if(h.tag===10)T=h.type===i.type?null:h.child;else if(h.tag===18){if(T=h.return,T===null)throw Error(n(341));T.lanes|=a,N=T.alternate,N!==null&&(N.lanes|=a),Ru(T,a,i),T=h.sibling}else T=h.child;if(T!==null)T.return=h;else for(T=h;T!==null;){if(T===i){T=null;break}if(h=T.sibling,h!==null){h.return=T.return,T=h;break}T=T.return}h=T}Sn(t,i,f.children,a),i=i.child}return i;case 9:return f=i.type,l=i.pendingProps.children,xs(i,a),f=$n(f),l=l(f),i.flags|=1,Sn(t,i,l,a),i.child;case 14:return l=i.type,f=oi(l,i.pendingProps),f=oi(l.type,f),Wh(t,i,l,f,a);case 15:return Xh(t,i,i.type,i.pendingProps,a);case 17:return l=i.type,f=i.pendingProps,f=i.elementType===l?f:oi(l,f),Fo(t,i),i.tag=1,Rn(l)?(t=!0,vo(i)):t=!1,xs(i,a),Fh(i,l,f),Wu(i,l,f,a),qu(null,i,l,!0,t,a);case 19:return Jh(t,i,a);case 22:return jh(t,i,a)}throw Error(n(156,i.tag))};function Ep(t,i){return Qa(t,i)}function V_(t,i,a,l){this.tag=t,this.key=a,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.ref=null,this.pendingProps=i,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=l,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function Qn(t,i,a,l){return new V_(t,i,a,l)}function pc(t){return t=t.prototype,!(!t||!t.isReactComponent)}function H_(t){if(typeof t=="function")return pc(t)?1:0;if(t!=null){if(t=t.$$typeof,t===te)return 11;if(t===K)return 14}return 2}function vr(t,i){var a=t.alternate;return a===null?(a=Qn(t.tag,i,t.key,t.mode),a.elementType=t.elementType,a.type=t.type,a.stateNode=t.stateNode,a.alternate=t,t.alternate=a):(a.pendingProps=i,a.type=t.type,a.flags=0,a.subtreeFlags=0,a.deletions=null),a.flags=t.flags&14680064,a.childLanes=t.childLanes,a.lanes=t.lanes,a.child=t.child,a.memoizedProps=t.memoizedProps,a.memoizedState=t.memoizedState,a.updateQueue=t.updateQueue,i=t.dependencies,a.dependencies=i===null?null:{lanes:i.lanes,firstContext:i.firstContext},a.sibling=t.sibling,a.index=t.index,a.ref=t.ref,a}function Yo(t,i,a,l,f,h){var T=2;if(l=t,typeof t=="function")pc(t)&&(T=1);else if(typeof t=="string")T=5;else e:switch(t){case z:return Gr(a.children,f,h,i);case A:T=8,f|=8;break;case D:return t=Qn(12,a,i,f|2),t.elementType=D,t.lanes=h,t;case Q:return t=Qn(13,a,i,f),t.elementType=Q,t.lanes=h,t;case oe:return t=Qn(19,a,i,f),t.elementType=oe,t.lanes=h,t;case W:return qo(a,f,h,i);default:if(typeof t=="object"&&t!==null)switch(t.$$typeof){case fe:T=10;break e;case O:T=9;break e;case te:T=11;break e;case K:T=14;break e;case ee:T=16,l=null;break e}throw Error(n(130,t==null?t:typeof t,""))}return i=Qn(T,a,i,f),i.elementType=t,i.type=l,i.lanes=h,i}function Gr(t,i,a,l){return t=Qn(7,t,l,i),t.lanes=a,t}function qo(t,i,a,l){return t=Qn(22,t,l,i),t.elementType=W,t.lanes=a,t.stateNode={isHidden:!1},t}function mc(t,i,a){return t=Qn(6,t,null,i),t.lanes=a,t}function gc(t,i,a){return i=Qn(4,t.children!==null?t.children:[],t.key,i),i.lanes=a,i.stateNode={containerInfo:t.containerInfo,pendingChildren:null,implementation:t.implementation},i}function G_(t,i,a,l,f){this.tag=i,this.containerInfo=t,this.finishedWork=this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.pendingContext=this.context=null,this.callbackPriority=0,this.eventTimes=An(0),this.expirationTimes=An(-1),this.entangledLanes=this.finishedLanes=this.mutableReadLanes=this.expiredLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=An(0),this.identifierPrefix=l,this.onRecoverableError=f,this.mutableSourceEagerHydrationData=null}function _c(t,i,a,l,f,h,T,N,B){return t=new G_(t,i,a,N,B),i===1?(i=1,h===!0&&(i|=8)):i=0,h=Qn(3,null,null,i),t.current=h,h.stateNode=t,h.memoizedState={element:l,isDehydrated:a,cache:null,transitions:null,pendingSuspenseBoundaries:null},Pu(h),t}function W_(t,i,a){var l=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:U,key:l==null?null:""+l,children:t,containerInfo:i,implementation:a}}function Tp(t){if(!t)return ur;t=t._reactInternals;e:{if(_i(t)!==t||t.tag!==1)throw Error(n(170));var i=t;do{switch(i.tag){case 3:i=i.stateNode.context;break e;case 1:if(Rn(i.type)){i=i.stateNode.__reactInternalMemoizedMergedChildContext;break e}}i=i.return}while(i!==null);throw Error(n(171))}if(t.tag===1){var a=t.type;if(Rn(a))return Qd(t,a,i)}return i}function wp(t,i,a,l,f,h,T,N,B){return t=_c(a,l,!0,t,f,h,T,N,B),t.context=Tp(null),a=t.current,l=yn(),f=gr(a),h=ki(l,f),h.callback=i??null,dr(a,h,f),t.current.lanes=f,Fn(t,f,l),Dn(t,l),t}function $o(t,i,a,l){var f=i.current,h=yn(),T=gr(f);return a=Tp(a),i.context===null?i.context=a:i.pendingContext=a,i=ki(h,T),i.payload={element:t},l=l===void 0?null:l,l!==null&&(i.callback=l),t=dr(f,i,T),t!==null&&(ci(t,f,T,h),Ao(t,f,T)),T}function Ko(t){if(t=t.current,!t.child)return null;switch(t.child.tag){case 5:return t.child.stateNode;default:return t.child.stateNode}}function Ap(t,i){if(t=t.memoizedState,t!==null&&t.dehydrated!==null){var a=t.retryLane;t.retryLane=a!==0&&a<i?a:i}}function vc(t,i){Ap(t,i),(t=t.alternate)&&Ap(t,i)}function X_(){return null}var Cp=typeof reportError=="function"?reportError:function(t){console.error(t)};function xc(t){this._internalRoot=t}Zo.prototype.render=xc.prototype.render=function(t){var i=this._internalRoot;if(i===null)throw Error(n(409));$o(t,i,null,null)},Zo.prototype.unmount=xc.prototype.unmount=function(){var t=this._internalRoot;if(t!==null){this._internalRoot=null;var i=t.containerInfo;zr(function(){$o(null,t,null,null)}),i[Ii]=null}};function Zo(t){this._internalRoot=t}Zo.prototype.unstable_scheduleHydration=function(t){if(t){var i=Zs();t={blockedOn:null,target:t,priority:i};for(var a=0;a<rr.length&&i!==0&&i<rr[a].priority;a++);rr.splice(a,0,t),a===0&&hd(t)}};function Sc(t){return!(!t||t.nodeType!==1&&t.nodeType!==9&&t.nodeType!==11)}function Qo(t){return!(!t||t.nodeType!==1&&t.nodeType!==9&&t.nodeType!==11&&(t.nodeType!==8||t.nodeValue!==" react-mount-point-unstable "))}function Rp(){}function j_(t,i,a,l,f){if(f){if(typeof l=="function"){var h=l;l=function(){var re=Ko(T);h.call(re)}}var T=wp(i,l,t,0,null,!1,!1,"",Rp);return t._reactRootContainer=T,t[Ii]=T.current,fa(t.nodeType===8?t.parentNode:t),zr(),T}for(;f=t.lastChild;)t.removeChild(f);if(typeof l=="function"){var N=l;l=function(){var re=Ko(B);N.call(re)}}var B=_c(t,0,!1,null,null,!1,!1,"",Rp);return t._reactRootContainer=B,t[Ii]=B.current,fa(t.nodeType===8?t.parentNode:t),zr(function(){$o(i,B,a,l)}),B}function Jo(t,i,a,l,f){var h=a._reactRootContainer;if(h){var T=h;if(typeof f=="function"){var N=f;f=function(){var B=Ko(T);N.call(B)}}$o(i,T,t,f)}else T=j_(a,i,t,f,l);return Ko(T)}jt=function(t){switch(t.tag){case 3:var i=t.stateNode;if(i.current.memoizedState.isDehydrated){var a=vt(i.pendingLanes);a!==0&&(At(i,a|1),Dn(i,w()),(Mt&6)===0&&(Ts=w()+500,cr()))}break;case 13:zr(function(){var l=Bi(t,1);if(l!==null){var f=yn();ci(l,t,1,f)}}),vc(t,1)}},jn=function(t){if(t.tag===13){var i=Bi(t,134217728);if(i!==null){var a=yn();ci(i,t,134217728,a)}vc(t,134217728)}},Ni=function(t){if(t.tag===13){var i=gr(t),a=Bi(t,i);if(a!==null){var l=yn();ci(a,t,i,l)}vc(t,i)}},Zs=function(){return st},fd=function(t,i){var a=st;try{return st=t,i()}finally{st=a}},Ae=function(t,i,a){switch(i){case"input":if(Ft(t,a),i=a.name,a.type==="radio"&&i!=null){for(a=t;a.parentNode;)a=a.parentNode;for(a=a.querySelectorAll("input[name="+JSON.stringify(""+i)+'][type="radio"]'),i=0;i<a.length;i++){var l=a[i];if(l!==t&&l.form===t.form){var f=go(l);if(!f)throw Error(n(90));Wt(l),Ft(l,f)}}}break;case"textarea":E(t,a);break;case"select":i=a.value,i!=null&&St(t,!!a.multiple,i,!1)}},rt=fc,Pt=zr;var Y_={usingClientEntryPoint:!1,Events:[pa,fs,go,ce,ze,fc]},Ra={findFiberByHostInstance:Lr,bundleType:0,version:"18.3.1",rendererPackageName:"react-dom"},q_={bundleType:Ra.bundleType,version:Ra.version,rendererPackageName:Ra.rendererPackageName,rendererConfig:Ra.rendererConfig,overrideHookState:null,overrideHookStateDeletePath:null,overrideHookStateRenamePath:null,overrideProps:null,overridePropsDeletePath:null,overridePropsRenamePath:null,setErrorHandler:null,setSuspenseHandler:null,scheduleUpdate:null,currentDispatcherRef:b.ReactCurrentDispatcher,findHostInstanceByFiber:function(t){return t=Ka(t),t===null?null:t.stateNode},findFiberByHostInstance:Ra.findFiberByHostInstance||X_,findHostInstancesForRefresh:null,scheduleRefresh:null,scheduleRoot:null,setRefreshHandler:null,getCurrentFiber:null,reconcilerVersion:"18.3.1-next-f1338f8080-20240426"};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<"u"){var el=__REACT_DEVTOOLS_GLOBAL_HOOK__;if(!el.isDisabled&&el.supportsFiber)try{Re=el.inject(q_),Ne=el}catch{}}return Ln.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=Y_,Ln.createPortal=function(t,i){var a=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!Sc(i))throw Error(n(200));return W_(t,i,null,a)},Ln.createRoot=function(t,i){if(!Sc(t))throw Error(n(299));var a=!1,l="",f=Cp;return i!=null&&(i.unstable_strictMode===!0&&(a=!0),i.identifierPrefix!==void 0&&(l=i.identifierPrefix),i.onRecoverableError!==void 0&&(f=i.onRecoverableError)),i=_c(t,1,!1,null,null,a,!1,l,f),t[Ii]=i.current,fa(t.nodeType===8?t.parentNode:t),new xc(i)},Ln.findDOMNode=function(t){if(t==null)return null;if(t.nodeType===1)return t;var i=t._reactInternals;if(i===void 0)throw typeof t.render=="function"?Error(n(188)):(t=Object.keys(t).join(","),Error(n(268,t)));return t=Ka(i),t=t===null?null:t.stateNode,t},Ln.flushSync=function(t){return zr(t)},Ln.hydrate=function(t,i,a){if(!Qo(i))throw Error(n(200));return Jo(null,t,i,!0,a)},Ln.hydrateRoot=function(t,i,a){if(!Sc(t))throw Error(n(405));var l=a!=null&&a.hydratedSources||null,f=!1,h="",T=Cp;if(a!=null&&(a.unstable_strictMode===!0&&(f=!0),a.identifierPrefix!==void 0&&(h=a.identifierPrefix),a.onRecoverableError!==void 0&&(T=a.onRecoverableError)),i=wp(i,null,t,1,a??null,f,!1,h,T),t[Ii]=i.current,fa(t),l)for(t=0;t<l.length;t++)a=l[t],f=a._getVersion,f=f(a._source),i.mutableSourceEagerHydrationData==null?i.mutableSourceEagerHydrationData=[a,f]:i.mutableSourceEagerHydrationData.push(a,f);return new Zo(i)},Ln.render=function(t,i,a){if(!Qo(i))throw Error(n(200));return Jo(null,t,i,!1,a)},Ln.unmountComponentAtNode=function(t){if(!Qo(t))throw Error(n(40));return t._reactRootContainer?(zr(function(){Jo(null,null,t,!1,function(){t._reactRootContainer=null,t[Ii]=null})}),!0):!1},Ln.unstable_batchedUpdates=fc,Ln.unstable_renderSubtreeIntoContainer=function(t,i,a,l){if(!Qo(a))throw Error(n(200));if(t==null||t._reactInternals===void 0)throw Error(n(38));return Jo(t,i,a,!1,l)},Ln.version="18.3.1-next-f1338f8080-20240426",Ln}var Fp;function i0(){if(Fp)return Ec.exports;Fp=1;function s(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(s)}catch(e){console.error(e)}}return s(),Ec.exports=n0(),Ec.exports}var Op;function r0(){if(Op)return tl;Op=1;var s=i0();return tl.createRoot=s.createRoot,tl.hydrateRoot=s.hydrateRoot,tl}var s0=r0();const a0=Um(s0);/**
 * @license
 * Copyright 2010-2026 Three.js Authors
 * SPDX-License-Identifier: MIT
 */const ed="183",o0=0,Bp=1,l0=2,Cl=1,u0=2,Oa=3,Rr=0,In=1,wi=2,qi=0,zs=1,kp=2,zp=3,Vp=4,c0=5,Zr=100,f0=101,d0=102,h0=103,p0=104,m0=200,g0=201,_0=202,v0=203,af=204,of=205,x0=206,S0=207,y0=208,M0=209,E0=210,T0=211,w0=212,A0=213,C0=214,lf=0,uf=1,cf=2,Hs=3,ff=4,df=5,hf=6,pf=7,Fm=0,R0=1,b0=2,Ri=0,Om=1,Bm=2,km=3,zm=4,Vm=5,Hm=6,Gm=7,Wm=300,ts=301,Gs=302,Ac=303,Cc=304,Bl=306,mf=1e3,Yi=1001,gf=1002,cn=1003,P0=1004,nl=1005,_n=1006,Rc=1007,Jr=1008,ni=1009,Xm=1010,jm=1011,za=1012,td=1013,Pi=1014,Ai=1015,Ki=1016,nd=1017,id=1018,Va=1020,Ym=35902,qm=35899,$m=1021,Km=1022,mi=1023,Zi=1026,es=1027,Zm=1028,rd=1029,Ws=1030,sd=1031,ad=1033,Rl=33776,bl=33777,Pl=33778,Dl=33779,_f=35840,vf=35841,xf=35842,Sf=35843,yf=36196,Mf=37492,Ef=37496,Tf=37488,wf=37489,Af=37490,Cf=37491,Rf=37808,bf=37809,Pf=37810,Df=37811,Lf=37812,Nf=37813,If=37814,Uf=37815,Ff=37816,Of=37817,Bf=37818,kf=37819,zf=37820,Vf=37821,Hf=36492,Gf=36494,Wf=36495,Xf=36283,jf=36284,Yf=36285,qf=36286,D0=3200,L0=0,N0=1,Ar="",ei="srgb",Xs="srgb-linear",Nl="linear",Dt="srgb",As=7680,Hp=519,I0=512,U0=513,F0=514,od=515,O0=516,B0=517,ld=518,k0=519,Gp=35044,Wp="300 es",Ci=2e3,Il=2001;function z0(s){for(let e=s.length-1;e>=0;--e)if(s[e]>=65535)return!0;return!1}function Ul(s){return document.createElementNS("http://www.w3.org/1999/xhtml",s)}function V0(){const s=Ul("canvas");return s.style.display="block",s}const Xp={};function jp(...s){const e="THREE."+s.shift();console.log(e,...s)}function Qm(s){const e=s[0];if(typeof e=="string"&&e.startsWith("TSL:")){const n=s[1];n&&n.isStackTrace?s[0]+=" "+n.getLocation():s[1]='Stack trace not available. Enable "THREE.Node.captureStackTrace" to capture stack traces.'}return s}function ot(...s){s=Qm(s);const e="THREE."+s.shift();{const n=s[0];n&&n.isStackTrace?console.warn(n.getError(e)):console.warn(e,...s)}}function wt(...s){s=Qm(s);const e="THREE."+s.shift();{const n=s[0];n&&n.isStackTrace?console.error(n.getError(e)):console.error(e,...s)}}function Fl(...s){const e=s.join(" ");e in Xp||(Xp[e]=!0,ot(...s))}function H0(s,e,n){return new Promise(function(r,o){function u(){switch(s.clientWaitSync(e,s.SYNC_FLUSH_COMMANDS_BIT,0)){case s.WAIT_FAILED:o();break;case s.TIMEOUT_EXPIRED:setTimeout(u,n);break;default:r()}}setTimeout(u,n)})}const G0={[lf]:uf,[cf]:hf,[ff]:pf,[Hs]:df,[uf]:lf,[hf]:cf,[pf]:ff,[df]:Hs};class Ys{addEventListener(e,n){this._listeners===void 0&&(this._listeners={});const r=this._listeners;r[e]===void 0&&(r[e]=[]),r[e].indexOf(n)===-1&&r[e].push(n)}hasEventListener(e,n){const r=this._listeners;return r===void 0?!1:r[e]!==void 0&&r[e].indexOf(n)!==-1}removeEventListener(e,n){const r=this._listeners;if(r===void 0)return;const o=r[e];if(o!==void 0){const u=o.indexOf(n);u!==-1&&o.splice(u,1)}}dispatchEvent(e){const n=this._listeners;if(n===void 0)return;const r=n[e.type];if(r!==void 0){e.target=this;const o=r.slice(0);for(let u=0,c=o.length;u<c;u++)o[u].call(this,e);e.target=null}}}const mn=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],bc=Math.PI/180,$f=180/Math.PI;function Ga(){const s=Math.random()*4294967295|0,e=Math.random()*4294967295|0,n=Math.random()*4294967295|0,r=Math.random()*4294967295|0;return(mn[s&255]+mn[s>>8&255]+mn[s>>16&255]+mn[s>>24&255]+"-"+mn[e&255]+mn[e>>8&255]+"-"+mn[e>>16&15|64]+mn[e>>24&255]+"-"+mn[n&63|128]+mn[n>>8&255]+"-"+mn[n>>16&255]+mn[n>>24&255]+mn[r&255]+mn[r>>8&255]+mn[r>>16&255]+mn[r>>24&255]).toLowerCase()}function _t(s,e,n){return Math.max(e,Math.min(n,s))}function W0(s,e){return(s%e+e)%e}function Pc(s,e,n){return(1-n)*s+n*e}function Pa(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return s/4294967295;case Uint16Array:return s/65535;case Uint8Array:return s/255;case Int32Array:return Math.max(s/2147483647,-1);case Int16Array:return Math.max(s/32767,-1);case Int8Array:return Math.max(s/127,-1);default:throw new Error("Invalid component type.")}}function Nn(s,e){switch(e.constructor){case Float32Array:return s;case Uint32Array:return Math.round(s*4294967295);case Uint16Array:return Math.round(s*65535);case Uint8Array:return Math.round(s*255);case Int32Array:return Math.round(s*2147483647);case Int16Array:return Math.round(s*32767);case Int8Array:return Math.round(s*127);default:throw new Error("Invalid component type.")}}class Lt{constructor(e=0,n=0){Lt.prototype.isVector2=!0,this.x=e,this.y=n}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,n){return this.x=e,this.y=n,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,n){switch(e){case 0:this.x=n;break;case 1:this.y=n;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,n){return this.x=e.x+n.x,this.y=e.y+n.y,this}addScaledVector(e,n){return this.x+=e.x*n,this.y+=e.y*n,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,n){return this.x=e.x-n.x,this.y=e.y-n.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){const n=this.x,r=this.y,o=e.elements;return this.x=o[0]*n+o[3]*r+o[6],this.y=o[1]*n+o[4]*r+o[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,n){return this.x=_t(this.x,e.x,n.x),this.y=_t(this.y,e.y,n.y),this}clampScalar(e,n){return this.x=_t(this.x,e,n),this.y=_t(this.y,e,n),this}clampLength(e,n){const r=this.length();return this.divideScalar(r||1).multiplyScalar(_t(r,e,n))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){const n=Math.sqrt(this.lengthSq()*e.lengthSq());if(n===0)return Math.PI/2;const r=this.dot(e)/n;return Math.acos(_t(r,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const n=this.x-e.x,r=this.y-e.y;return n*n+r*r}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,n){return this.x+=(e.x-this.x)*n,this.y+=(e.y-this.y)*n,this}lerpVectors(e,n,r){return this.x=e.x+(n.x-e.x)*r,this.y=e.y+(n.y-e.y)*r,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,n=0){return this.x=e[n],this.y=e[n+1],this}toArray(e=[],n=0){return e[n]=this.x,e[n+1]=this.y,e}fromBufferAttribute(e,n){return this.x=e.getX(n),this.y=e.getY(n),this}rotateAround(e,n){const r=Math.cos(n),o=Math.sin(n),u=this.x-e.x,c=this.y-e.y;return this.x=u*r-c*o+e.x,this.y=u*o+c*r+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class qs{constructor(e=0,n=0,r=0,o=1){this.isQuaternion=!0,this._x=e,this._y=n,this._z=r,this._w=o}static slerpFlat(e,n,r,o,u,c,d){let p=r[o+0],m=r[o+1],x=r[o+2],S=r[o+3],g=u[c+0],y=u[c+1],M=u[c+2],C=u[c+3];if(S!==C||p!==g||m!==y||x!==M){let _=p*g+m*y+x*M+S*C;_<0&&(g=-g,y=-y,M=-M,C=-C,_=-_);let v=1-d;if(_<.9995){const R=Math.acos(_),L=Math.sin(R);v=Math.sin(v*R)/L,d=Math.sin(d*R)/L,p=p*v+g*d,m=m*v+y*d,x=x*v+M*d,S=S*v+C*d}else{p=p*v+g*d,m=m*v+y*d,x=x*v+M*d,S=S*v+C*d;const R=1/Math.sqrt(p*p+m*m+x*x+S*S);p*=R,m*=R,x*=R,S*=R}}e[n]=p,e[n+1]=m,e[n+2]=x,e[n+3]=S}static multiplyQuaternionsFlat(e,n,r,o,u,c){const d=r[o],p=r[o+1],m=r[o+2],x=r[o+3],S=u[c],g=u[c+1],y=u[c+2],M=u[c+3];return e[n]=d*M+x*S+p*y-m*g,e[n+1]=p*M+x*g+m*S-d*y,e[n+2]=m*M+x*y+d*g-p*S,e[n+3]=x*M-d*S-p*g-m*y,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,n,r,o){return this._x=e,this._y=n,this._z=r,this._w=o,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,n=!0){const r=e._x,o=e._y,u=e._z,c=e._order,d=Math.cos,p=Math.sin,m=d(r/2),x=d(o/2),S=d(u/2),g=p(r/2),y=p(o/2),M=p(u/2);switch(c){case"XYZ":this._x=g*x*S+m*y*M,this._y=m*y*S-g*x*M,this._z=m*x*M+g*y*S,this._w=m*x*S-g*y*M;break;case"YXZ":this._x=g*x*S+m*y*M,this._y=m*y*S-g*x*M,this._z=m*x*M-g*y*S,this._w=m*x*S+g*y*M;break;case"ZXY":this._x=g*x*S-m*y*M,this._y=m*y*S+g*x*M,this._z=m*x*M+g*y*S,this._w=m*x*S-g*y*M;break;case"ZYX":this._x=g*x*S-m*y*M,this._y=m*y*S+g*x*M,this._z=m*x*M-g*y*S,this._w=m*x*S+g*y*M;break;case"YZX":this._x=g*x*S+m*y*M,this._y=m*y*S+g*x*M,this._z=m*x*M-g*y*S,this._w=m*x*S-g*y*M;break;case"XZY":this._x=g*x*S-m*y*M,this._y=m*y*S-g*x*M,this._z=m*x*M+g*y*S,this._w=m*x*S+g*y*M;break;default:ot("Quaternion: .setFromEuler() encountered an unknown order: "+c)}return n===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,n){const r=n/2,o=Math.sin(r);return this._x=e.x*o,this._y=e.y*o,this._z=e.z*o,this._w=Math.cos(r),this._onChangeCallback(),this}setFromRotationMatrix(e){const n=e.elements,r=n[0],o=n[4],u=n[8],c=n[1],d=n[5],p=n[9],m=n[2],x=n[6],S=n[10],g=r+d+S;if(g>0){const y=.5/Math.sqrt(g+1);this._w=.25/y,this._x=(x-p)*y,this._y=(u-m)*y,this._z=(c-o)*y}else if(r>d&&r>S){const y=2*Math.sqrt(1+r-d-S);this._w=(x-p)/y,this._x=.25*y,this._y=(o+c)/y,this._z=(u+m)/y}else if(d>S){const y=2*Math.sqrt(1+d-r-S);this._w=(u-m)/y,this._x=(o+c)/y,this._y=.25*y,this._z=(p+x)/y}else{const y=2*Math.sqrt(1+S-r-d);this._w=(c-o)/y,this._x=(u+m)/y,this._y=(p+x)/y,this._z=.25*y}return this._onChangeCallback(),this}setFromUnitVectors(e,n){let r=e.dot(n)+1;return r<1e-8?(r=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=r):(this._x=0,this._y=-e.z,this._z=e.y,this._w=r)):(this._x=e.y*n.z-e.z*n.y,this._y=e.z*n.x-e.x*n.z,this._z=e.x*n.y-e.y*n.x,this._w=r),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(_t(this.dot(e),-1,1)))}rotateTowards(e,n){const r=this.angleTo(e);if(r===0)return this;const o=Math.min(1,n/r);return this.slerp(e,o),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,n){const r=e._x,o=e._y,u=e._z,c=e._w,d=n._x,p=n._y,m=n._z,x=n._w;return this._x=r*x+c*d+o*m-u*p,this._y=o*x+c*p+u*d-r*m,this._z=u*x+c*m+r*p-o*d,this._w=c*x-r*d-o*p-u*m,this._onChangeCallback(),this}slerp(e,n){let r=e._x,o=e._y,u=e._z,c=e._w,d=this.dot(e);d<0&&(r=-r,o=-o,u=-u,c=-c,d=-d);let p=1-n;if(d<.9995){const m=Math.acos(d),x=Math.sin(m);p=Math.sin(p*m)/x,n=Math.sin(n*m)/x,this._x=this._x*p+r*n,this._y=this._y*p+o*n,this._z=this._z*p+u*n,this._w=this._w*p+c*n,this._onChangeCallback()}else this._x=this._x*p+r*n,this._y=this._y*p+o*n,this._z=this._z*p+u*n,this._w=this._w*p+c*n,this.normalize();return this}slerpQuaternions(e,n,r){return this.copy(e).slerp(n,r)}random(){const e=2*Math.PI*Math.random(),n=2*Math.PI*Math.random(),r=Math.random(),o=Math.sqrt(1-r),u=Math.sqrt(r);return this.set(o*Math.sin(e),o*Math.cos(e),u*Math.sin(n),u*Math.cos(n))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,n=0){return this._x=e[n],this._y=e[n+1],this._z=e[n+2],this._w=e[n+3],this._onChangeCallback(),this}toArray(e=[],n=0){return e[n]=this._x,e[n+1]=this._y,e[n+2]=this._z,e[n+3]=this._w,e}fromBufferAttribute(e,n){return this._x=e.getX(n),this._y=e.getY(n),this._z=e.getZ(n),this._w=e.getW(n),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class ne{constructor(e=0,n=0,r=0){ne.prototype.isVector3=!0,this.x=e,this.y=n,this.z=r}set(e,n,r){return r===void 0&&(r=this.z),this.x=e,this.y=n,this.z=r,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,n){switch(e){case 0:this.x=n;break;case 1:this.y=n;break;case 2:this.z=n;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,n){return this.x=e.x+n.x,this.y=e.y+n.y,this.z=e.z+n.z,this}addScaledVector(e,n){return this.x+=e.x*n,this.y+=e.y*n,this.z+=e.z*n,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,n){return this.x=e.x-n.x,this.y=e.y-n.y,this.z=e.z-n.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,n){return this.x=e.x*n.x,this.y=e.y*n.y,this.z=e.z*n.z,this}applyEuler(e){return this.applyQuaternion(Yp.setFromEuler(e))}applyAxisAngle(e,n){return this.applyQuaternion(Yp.setFromAxisAngle(e,n))}applyMatrix3(e){const n=this.x,r=this.y,o=this.z,u=e.elements;return this.x=u[0]*n+u[3]*r+u[6]*o,this.y=u[1]*n+u[4]*r+u[7]*o,this.z=u[2]*n+u[5]*r+u[8]*o,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){const n=this.x,r=this.y,o=this.z,u=e.elements,c=1/(u[3]*n+u[7]*r+u[11]*o+u[15]);return this.x=(u[0]*n+u[4]*r+u[8]*o+u[12])*c,this.y=(u[1]*n+u[5]*r+u[9]*o+u[13])*c,this.z=(u[2]*n+u[6]*r+u[10]*o+u[14])*c,this}applyQuaternion(e){const n=this.x,r=this.y,o=this.z,u=e.x,c=e.y,d=e.z,p=e.w,m=2*(c*o-d*r),x=2*(d*n-u*o),S=2*(u*r-c*n);return this.x=n+p*m+c*S-d*x,this.y=r+p*x+d*m-u*S,this.z=o+p*S+u*x-c*m,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){const n=this.x,r=this.y,o=this.z,u=e.elements;return this.x=u[0]*n+u[4]*r+u[8]*o,this.y=u[1]*n+u[5]*r+u[9]*o,this.z=u[2]*n+u[6]*r+u[10]*o,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,n){return this.x=_t(this.x,e.x,n.x),this.y=_t(this.y,e.y,n.y),this.z=_t(this.z,e.z,n.z),this}clampScalar(e,n){return this.x=_t(this.x,e,n),this.y=_t(this.y,e,n),this.z=_t(this.z,e,n),this}clampLength(e,n){const r=this.length();return this.divideScalar(r||1).multiplyScalar(_t(r,e,n))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,n){return this.x+=(e.x-this.x)*n,this.y+=(e.y-this.y)*n,this.z+=(e.z-this.z)*n,this}lerpVectors(e,n,r){return this.x=e.x+(n.x-e.x)*r,this.y=e.y+(n.y-e.y)*r,this.z=e.z+(n.z-e.z)*r,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,n){const r=e.x,o=e.y,u=e.z,c=n.x,d=n.y,p=n.z;return this.x=o*p-u*d,this.y=u*c-r*p,this.z=r*d-o*c,this}projectOnVector(e){const n=e.lengthSq();if(n===0)return this.set(0,0,0);const r=e.dot(this)/n;return this.copy(e).multiplyScalar(r)}projectOnPlane(e){return Dc.copy(this).projectOnVector(e),this.sub(Dc)}reflect(e){return this.sub(Dc.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){const n=Math.sqrt(this.lengthSq()*e.lengthSq());if(n===0)return Math.PI/2;const r=this.dot(e)/n;return Math.acos(_t(r,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){const n=this.x-e.x,r=this.y-e.y,o=this.z-e.z;return n*n+r*r+o*o}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,n,r){const o=Math.sin(n)*e;return this.x=o*Math.sin(r),this.y=Math.cos(n)*e,this.z=o*Math.cos(r),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,n,r){return this.x=e*Math.sin(n),this.y=r,this.z=e*Math.cos(n),this}setFromMatrixPosition(e){const n=e.elements;return this.x=n[12],this.y=n[13],this.z=n[14],this}setFromMatrixScale(e){const n=this.setFromMatrixColumn(e,0).length(),r=this.setFromMatrixColumn(e,1).length(),o=this.setFromMatrixColumn(e,2).length();return this.x=n,this.y=r,this.z=o,this}setFromMatrixColumn(e,n){return this.fromArray(e.elements,n*4)}setFromMatrix3Column(e,n){return this.fromArray(e.elements,n*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,n=0){return this.x=e[n],this.y=e[n+1],this.z=e[n+2],this}toArray(e=[],n=0){return e[n]=this.x,e[n+1]=this.y,e[n+2]=this.z,e}fromBufferAttribute(e,n){return this.x=e.getX(n),this.y=e.getY(n),this.z=e.getZ(n),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const e=Math.random()*Math.PI*2,n=Math.random()*2-1,r=Math.sqrt(1-n*n);return this.x=r*Math.cos(e),this.y=n,this.z=r*Math.sin(e),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const Dc=new ne,Yp=new qs;class ft{constructor(e,n,r,o,u,c,d,p,m){ft.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,n,r,o,u,c,d,p,m)}set(e,n,r,o,u,c,d,p,m){const x=this.elements;return x[0]=e,x[1]=o,x[2]=d,x[3]=n,x[4]=u,x[5]=p,x[6]=r,x[7]=c,x[8]=m,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){const n=this.elements,r=e.elements;return n[0]=r[0],n[1]=r[1],n[2]=r[2],n[3]=r[3],n[4]=r[4],n[5]=r[5],n[6]=r[6],n[7]=r[7],n[8]=r[8],this}extractBasis(e,n,r){return e.setFromMatrix3Column(this,0),n.setFromMatrix3Column(this,1),r.setFromMatrix3Column(this,2),this}setFromMatrix4(e){const n=e.elements;return this.set(n[0],n[4],n[8],n[1],n[5],n[9],n[2],n[6],n[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,n){const r=e.elements,o=n.elements,u=this.elements,c=r[0],d=r[3],p=r[6],m=r[1],x=r[4],S=r[7],g=r[2],y=r[5],M=r[8],C=o[0],_=o[3],v=o[6],R=o[1],L=o[4],b=o[7],F=o[2],U=o[5],z=o[8];return u[0]=c*C+d*R+p*F,u[3]=c*_+d*L+p*U,u[6]=c*v+d*b+p*z,u[1]=m*C+x*R+S*F,u[4]=m*_+x*L+S*U,u[7]=m*v+x*b+S*z,u[2]=g*C+y*R+M*F,u[5]=g*_+y*L+M*U,u[8]=g*v+y*b+M*z,this}multiplyScalar(e){const n=this.elements;return n[0]*=e,n[3]*=e,n[6]*=e,n[1]*=e,n[4]*=e,n[7]*=e,n[2]*=e,n[5]*=e,n[8]*=e,this}determinant(){const e=this.elements,n=e[0],r=e[1],o=e[2],u=e[3],c=e[4],d=e[5],p=e[6],m=e[7],x=e[8];return n*c*x-n*d*m-r*u*x+r*d*p+o*u*m-o*c*p}invert(){const e=this.elements,n=e[0],r=e[1],o=e[2],u=e[3],c=e[4],d=e[5],p=e[6],m=e[7],x=e[8],S=x*c-d*m,g=d*p-x*u,y=m*u-c*p,M=n*S+r*g+o*y;if(M===0)return this.set(0,0,0,0,0,0,0,0,0);const C=1/M;return e[0]=S*C,e[1]=(o*m-x*r)*C,e[2]=(d*r-o*c)*C,e[3]=g*C,e[4]=(x*n-o*p)*C,e[5]=(o*u-d*n)*C,e[6]=y*C,e[7]=(r*p-m*n)*C,e[8]=(c*n-r*u)*C,this}transpose(){let e;const n=this.elements;return e=n[1],n[1]=n[3],n[3]=e,e=n[2],n[2]=n[6],n[6]=e,e=n[5],n[5]=n[7],n[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){const n=this.elements;return e[0]=n[0],e[1]=n[3],e[2]=n[6],e[3]=n[1],e[4]=n[4],e[5]=n[7],e[6]=n[2],e[7]=n[5],e[8]=n[8],this}setUvTransform(e,n,r,o,u,c,d){const p=Math.cos(u),m=Math.sin(u);return this.set(r*p,r*m,-r*(p*c+m*d)+c+e,-o*m,o*p,-o*(-m*c+p*d)+d+n,0,0,1),this}scale(e,n){return this.premultiply(Lc.makeScale(e,n)),this}rotate(e){return this.premultiply(Lc.makeRotation(-e)),this}translate(e,n){return this.premultiply(Lc.makeTranslation(e,n)),this}makeTranslation(e,n){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,n,0,0,1),this}makeRotation(e){const n=Math.cos(e),r=Math.sin(e);return this.set(n,-r,0,r,n,0,0,0,1),this}makeScale(e,n){return this.set(e,0,0,0,n,0,0,0,1),this}equals(e){const n=this.elements,r=e.elements;for(let o=0;o<9;o++)if(n[o]!==r[o])return!1;return!0}fromArray(e,n=0){for(let r=0;r<9;r++)this.elements[r]=e[r+n];return this}toArray(e=[],n=0){const r=this.elements;return e[n]=r[0],e[n+1]=r[1],e[n+2]=r[2],e[n+3]=r[3],e[n+4]=r[4],e[n+5]=r[5],e[n+6]=r[6],e[n+7]=r[7],e[n+8]=r[8],e}clone(){return new this.constructor().fromArray(this.elements)}}const Lc=new ft,qp=new ft().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),$p=new ft().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function X0(){const s={enabled:!0,workingColorSpace:Xs,spaces:{},convert:function(o,u,c){return this.enabled===!1||u===c||!u||!c||(this.spaces[u].transfer===Dt&&(o.r=$i(o.r),o.g=$i(o.g),o.b=$i(o.b)),this.spaces[u].primaries!==this.spaces[c].primaries&&(o.applyMatrix3(this.spaces[u].toXYZ),o.applyMatrix3(this.spaces[c].fromXYZ)),this.spaces[c].transfer===Dt&&(o.r=Vs(o.r),o.g=Vs(o.g),o.b=Vs(o.b))),o},workingToColorSpace:function(o,u){return this.convert(o,this.workingColorSpace,u)},colorSpaceToWorking:function(o,u){return this.convert(o,u,this.workingColorSpace)},getPrimaries:function(o){return this.spaces[o].primaries},getTransfer:function(o){return o===Ar?Nl:this.spaces[o].transfer},getToneMappingMode:function(o){return this.spaces[o].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(o,u=this.workingColorSpace){return o.fromArray(this.spaces[u].luminanceCoefficients)},define:function(o){Object.assign(this.spaces,o)},_getMatrix:function(o,u,c){return o.copy(this.spaces[u].toXYZ).multiply(this.spaces[c].fromXYZ)},_getDrawingBufferColorSpace:function(o){return this.spaces[o].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(o=this.workingColorSpace){return this.spaces[o].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(o,u){return Fl("ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),s.workingToColorSpace(o,u)},toWorkingColorSpace:function(o,u){return Fl("ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),s.colorSpaceToWorking(o,u)}},e=[.64,.33,.3,.6,.15,.06],n=[.2126,.7152,.0722],r=[.3127,.329];return s.define({[Xs]:{primaries:e,whitePoint:r,transfer:Nl,toXYZ:qp,fromXYZ:$p,luminanceCoefficients:n,workingColorSpaceConfig:{unpackColorSpace:ei},outputColorSpaceConfig:{drawingBufferColorSpace:ei}},[ei]:{primaries:e,whitePoint:r,transfer:Dt,toXYZ:qp,fromXYZ:$p,luminanceCoefficients:n,outputColorSpaceConfig:{drawingBufferColorSpace:ei}}}),s}const Et=X0();function $i(s){return s<.04045?s*.0773993808:Math.pow(s*.9478672986+.0521327014,2.4)}function Vs(s){return s<.0031308?s*12.92:1.055*Math.pow(s,.41666)-.055}let Cs;class j0{static getDataURL(e,n="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let r;if(e instanceof HTMLCanvasElement)r=e;else{Cs===void 0&&(Cs=Ul("canvas")),Cs.width=e.width,Cs.height=e.height;const o=Cs.getContext("2d");e instanceof ImageData?o.putImageData(e,0,0):o.drawImage(e,0,0,e.width,e.height),r=Cs}return r.toDataURL(n)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){const n=Ul("canvas");n.width=e.width,n.height=e.height;const r=n.getContext("2d");r.drawImage(e,0,0,e.width,e.height);const o=r.getImageData(0,0,e.width,e.height),u=o.data;for(let c=0;c<u.length;c++)u[c]=$i(u[c]/255)*255;return r.putImageData(o,0,0),n}else if(e.data){const n=e.data.slice(0);for(let r=0;r<n.length;r++)n instanceof Uint8Array||n instanceof Uint8ClampedArray?n[r]=Math.floor($i(n[r]/255)*255):n[r]=$i(n[r]);return{data:n,width:e.width,height:e.height}}else return ot("ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}}let Y0=0;class ud{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Y0++}),this.uuid=Ga(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){const n=this.data;return typeof HTMLVideoElement<"u"&&n instanceof HTMLVideoElement?e.set(n.videoWidth,n.videoHeight,0):typeof VideoFrame<"u"&&n instanceof VideoFrame?e.set(n.displayHeight,n.displayWidth,0):n!==null?e.set(n.width,n.height,n.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){const n=e===void 0||typeof e=="string";if(!n&&e.images[this.uuid]!==void 0)return e.images[this.uuid];const r={uuid:this.uuid,url:""},o=this.data;if(o!==null){let u;if(Array.isArray(o)){u=[];for(let c=0,d=o.length;c<d;c++)o[c].isDataTexture?u.push(Nc(o[c].image)):u.push(Nc(o[c]))}else u=Nc(o);r.url=u}return n||(e.images[this.uuid]=r),r}}function Nc(s){return typeof HTMLImageElement<"u"&&s instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&s instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&s instanceof ImageBitmap?j0.getDataURL(s):s.data?{data:Array.from(s.data),width:s.width,height:s.height,type:s.data.constructor.name}:(ot("Texture: Unable to serialize Texture."),{})}let q0=0;const Ic=new ne;class En extends Ys{constructor(e=En.DEFAULT_IMAGE,n=En.DEFAULT_MAPPING,r=Yi,o=Yi,u=_n,c=Jr,d=mi,p=ni,m=En.DEFAULT_ANISOTROPY,x=Ar){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:q0++}),this.uuid=Ga(),this.name="",this.source=new ud(e),this.mipmaps=[],this.mapping=n,this.channel=0,this.wrapS=r,this.wrapT=o,this.magFilter=u,this.minFilter=c,this.anisotropy=m,this.format=d,this.internalFormat=null,this.type=p,this.offset=new Lt(0,0),this.repeat=new Lt(1,1),this.center=new Lt(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new ft,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=x,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(e&&e.depth&&e.depth>1),this.pmremVersion=0}get width(){return this.source.getSize(Ic).x}get height(){return this.source.getSize(Ic).y}get depth(){return this.source.getSize(Ic).z}get image(){return this.source.data}set image(e=null){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(e,n){this.updateRanges.push({start:e,count:n})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.renderTarget=e.renderTarget,this.isRenderTargetTexture=e.isRenderTargetTexture,this.isArrayTexture=e.isArrayTexture,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}setValues(e){for(const n in e){const r=e[n];if(r===void 0){ot(`Texture.setValues(): parameter '${n}' has value of undefined.`);continue}const o=this[n];if(o===void 0){ot(`Texture.setValues(): property '${n}' does not exist.`);continue}o&&r&&o.isVector2&&r.isVector2||o&&r&&o.isVector3&&r.isVector3||o&&r&&o.isMatrix3&&r.isMatrix3?o.copy(r):this[n]=r}}toJSON(e){const n=e===void 0||typeof e=="string";if(!n&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];const r={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(r.userData=this.userData),n||(e.textures[this.uuid]=r),r}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==Wm)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case mf:e.x=e.x-Math.floor(e.x);break;case Yi:e.x=e.x<0?0:1;break;case gf:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case mf:e.y=e.y-Math.floor(e.y);break;case Yi:e.y=e.y<0?0:1;break;case gf:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(e){e===!0&&this.pmremVersion++}}En.DEFAULT_IMAGE=null;En.DEFAULT_MAPPING=Wm;En.DEFAULT_ANISOTROPY=1;class qt{constructor(e=0,n=0,r=0,o=1){qt.prototype.isVector4=!0,this.x=e,this.y=n,this.z=r,this.w=o}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,n,r,o){return this.x=e,this.y=n,this.z=r,this.w=o,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,n){switch(e){case 0:this.x=n;break;case 1:this.y=n;break;case 2:this.z=n;break;case 3:this.w=n;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,n){return this.x=e.x+n.x,this.y=e.y+n.y,this.z=e.z+n.z,this.w=e.w+n.w,this}addScaledVector(e,n){return this.x+=e.x*n,this.y+=e.y*n,this.z+=e.z*n,this.w+=e.w*n,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,n){return this.x=e.x-n.x,this.y=e.y-n.y,this.z=e.z-n.z,this.w=e.w-n.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){const n=this.x,r=this.y,o=this.z,u=this.w,c=e.elements;return this.x=c[0]*n+c[4]*r+c[8]*o+c[12]*u,this.y=c[1]*n+c[5]*r+c[9]*o+c[13]*u,this.z=c[2]*n+c[6]*r+c[10]*o+c[14]*u,this.w=c[3]*n+c[7]*r+c[11]*o+c[15]*u,this}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this.w/=e.w,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);const n=Math.sqrt(1-e.w*e.w);return n<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/n,this.y=e.y/n,this.z=e.z/n),this}setAxisAngleFromRotationMatrix(e){let n,r,o,u;const p=e.elements,m=p[0],x=p[4],S=p[8],g=p[1],y=p[5],M=p[9],C=p[2],_=p[6],v=p[10];if(Math.abs(x-g)<.01&&Math.abs(S-C)<.01&&Math.abs(M-_)<.01){if(Math.abs(x+g)<.1&&Math.abs(S+C)<.1&&Math.abs(M+_)<.1&&Math.abs(m+y+v-3)<.1)return this.set(1,0,0,0),this;n=Math.PI;const L=(m+1)/2,b=(y+1)/2,F=(v+1)/2,U=(x+g)/4,z=(S+C)/4,A=(M+_)/4;return L>b&&L>F?L<.01?(r=0,o=.707106781,u=.707106781):(r=Math.sqrt(L),o=U/r,u=z/r):b>F?b<.01?(r=.707106781,o=0,u=.707106781):(o=Math.sqrt(b),r=U/o,u=A/o):F<.01?(r=.707106781,o=.707106781,u=0):(u=Math.sqrt(F),r=z/u,o=A/u),this.set(r,o,u,n),this}let R=Math.sqrt((_-M)*(_-M)+(S-C)*(S-C)+(g-x)*(g-x));return Math.abs(R)<.001&&(R=1),this.x=(_-M)/R,this.y=(S-C)/R,this.z=(g-x)/R,this.w=Math.acos((m+y+v-1)/2),this}setFromMatrixPosition(e){const n=e.elements;return this.x=n[12],this.y=n[13],this.z=n[14],this.w=n[15],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,n){return this.x=_t(this.x,e.x,n.x),this.y=_t(this.y,e.y,n.y),this.z=_t(this.z,e.z,n.z),this.w=_t(this.w,e.w,n.w),this}clampScalar(e,n){return this.x=_t(this.x,e,n),this.y=_t(this.y,e,n),this.z=_t(this.z,e,n),this.w=_t(this.w,e,n),this}clampLength(e,n){const r=this.length();return this.divideScalar(r||1).multiplyScalar(_t(r,e,n))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,n){return this.x+=(e.x-this.x)*n,this.y+=(e.y-this.y)*n,this.z+=(e.z-this.z)*n,this.w+=(e.w-this.w)*n,this}lerpVectors(e,n,r){return this.x=e.x+(n.x-e.x)*r,this.y=e.y+(n.y-e.y)*r,this.z=e.z+(n.z-e.z)*r,this.w=e.w+(n.w-e.w)*r,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,n=0){return this.x=e[n],this.y=e[n+1],this.z=e[n+2],this.w=e[n+3],this}toArray(e=[],n=0){return e[n]=this.x,e[n+1]=this.y,e[n+2]=this.z,e[n+3]=this.w,e}fromBufferAttribute(e,n){return this.x=e.getX(n),this.y=e.getY(n),this.z=e.getZ(n),this.w=e.getW(n),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class $0 extends Ys{constructor(e=1,n=1,r={}){super(),r=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:_n,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1},r),this.isRenderTarget=!0,this.width=e,this.height=n,this.depth=r.depth,this.scissor=new qt(0,0,e,n),this.scissorTest=!1,this.viewport=new qt(0,0,e,n),this.textures=[];const o={width:e,height:n,depth:r.depth},u=new En(o),c=r.count;for(let d=0;d<c;d++)this.textures[d]=u.clone(),this.textures[d].isRenderTargetTexture=!0,this.textures[d].renderTarget=this;this._setTextureOptions(r),this.depthBuffer=r.depthBuffer,this.stencilBuffer=r.stencilBuffer,this.resolveDepthBuffer=r.resolveDepthBuffer,this.resolveStencilBuffer=r.resolveStencilBuffer,this._depthTexture=null,this.depthTexture=r.depthTexture,this.samples=r.samples,this.multiview=r.multiview}_setTextureOptions(e={}){const n={minFilter:_n,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(n.mapping=e.mapping),e.wrapS!==void 0&&(n.wrapS=e.wrapS),e.wrapT!==void 0&&(n.wrapT=e.wrapT),e.wrapR!==void 0&&(n.wrapR=e.wrapR),e.magFilter!==void 0&&(n.magFilter=e.magFilter),e.minFilter!==void 0&&(n.minFilter=e.minFilter),e.format!==void 0&&(n.format=e.format),e.type!==void 0&&(n.type=e.type),e.anisotropy!==void 0&&(n.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(n.colorSpace=e.colorSpace),e.flipY!==void 0&&(n.flipY=e.flipY),e.generateMipmaps!==void 0&&(n.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(n.internalFormat=e.internalFormat);for(let r=0;r<this.textures.length;r++)this.textures[r].setValues(n)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&(this._depthTexture.renderTarget=null),e!==null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,n,r=1){if(this.width!==e||this.height!==n||this.depth!==r){this.width=e,this.height=n,this.depth=r;for(let o=0,u=this.textures.length;o<u;o++)this.textures[o].image.width=e,this.textures[o].image.height=n,this.textures[o].image.depth=r,this.textures[o].isData3DTexture!==!0&&(this.textures[o].isArrayTexture=this.textures[o].image.depth>1);this.dispose()}this.viewport.set(0,0,e,n),this.scissor.set(0,0,e,n)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let n=0,r=e.textures.length;n<r;n++){this.textures[n]=e.textures[n].clone(),this.textures[n].isRenderTargetTexture=!0,this.textures[n].renderTarget=this;const o=Object.assign({},e.textures[n].image);this.textures[n].source=new ud(o)}return this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class bi extends $0{constructor(e=1,n=1,r={}){super(e,n,r),this.isWebGLRenderTarget=!0}}class Jm extends En{constructor(e=null,n=1,r=1,o=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:n,height:r,depth:o},this.magFilter=cn,this.minFilter=cn,this.wrapR=Yi,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}}class K0 extends En{constructor(e=null,n=1,r=1,o=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:n,height:r,depth:o},this.magFilter=cn,this.minFilter=cn,this.wrapR=Yi,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class $t{constructor(e,n,r,o,u,c,d,p,m,x,S,g,y,M,C,_){$t.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,n,r,o,u,c,d,p,m,x,S,g,y,M,C,_)}set(e,n,r,o,u,c,d,p,m,x,S,g,y,M,C,_){const v=this.elements;return v[0]=e,v[4]=n,v[8]=r,v[12]=o,v[1]=u,v[5]=c,v[9]=d,v[13]=p,v[2]=m,v[6]=x,v[10]=S,v[14]=g,v[3]=y,v[7]=M,v[11]=C,v[15]=_,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new $t().fromArray(this.elements)}copy(e){const n=this.elements,r=e.elements;return n[0]=r[0],n[1]=r[1],n[2]=r[2],n[3]=r[3],n[4]=r[4],n[5]=r[5],n[6]=r[6],n[7]=r[7],n[8]=r[8],n[9]=r[9],n[10]=r[10],n[11]=r[11],n[12]=r[12],n[13]=r[13],n[14]=r[14],n[15]=r[15],this}copyPosition(e){const n=this.elements,r=e.elements;return n[12]=r[12],n[13]=r[13],n[14]=r[14],this}setFromMatrix3(e){const n=e.elements;return this.set(n[0],n[3],n[6],0,n[1],n[4],n[7],0,n[2],n[5],n[8],0,0,0,0,1),this}extractBasis(e,n,r){return this.determinant()===0?(e.set(1,0,0),n.set(0,1,0),r.set(0,0,1),this):(e.setFromMatrixColumn(this,0),n.setFromMatrixColumn(this,1),r.setFromMatrixColumn(this,2),this)}makeBasis(e,n,r){return this.set(e.x,n.x,r.x,0,e.y,n.y,r.y,0,e.z,n.z,r.z,0,0,0,0,1),this}extractRotation(e){if(e.determinant()===0)return this.identity();const n=this.elements,r=e.elements,o=1/Rs.setFromMatrixColumn(e,0).length(),u=1/Rs.setFromMatrixColumn(e,1).length(),c=1/Rs.setFromMatrixColumn(e,2).length();return n[0]=r[0]*o,n[1]=r[1]*o,n[2]=r[2]*o,n[3]=0,n[4]=r[4]*u,n[5]=r[5]*u,n[6]=r[6]*u,n[7]=0,n[8]=r[8]*c,n[9]=r[9]*c,n[10]=r[10]*c,n[11]=0,n[12]=0,n[13]=0,n[14]=0,n[15]=1,this}makeRotationFromEuler(e){const n=this.elements,r=e.x,o=e.y,u=e.z,c=Math.cos(r),d=Math.sin(r),p=Math.cos(o),m=Math.sin(o),x=Math.cos(u),S=Math.sin(u);if(e.order==="XYZ"){const g=c*x,y=c*S,M=d*x,C=d*S;n[0]=p*x,n[4]=-p*S,n[8]=m,n[1]=y+M*m,n[5]=g-C*m,n[9]=-d*p,n[2]=C-g*m,n[6]=M+y*m,n[10]=c*p}else if(e.order==="YXZ"){const g=p*x,y=p*S,M=m*x,C=m*S;n[0]=g+C*d,n[4]=M*d-y,n[8]=c*m,n[1]=c*S,n[5]=c*x,n[9]=-d,n[2]=y*d-M,n[6]=C+g*d,n[10]=c*p}else if(e.order==="ZXY"){const g=p*x,y=p*S,M=m*x,C=m*S;n[0]=g-C*d,n[4]=-c*S,n[8]=M+y*d,n[1]=y+M*d,n[5]=c*x,n[9]=C-g*d,n[2]=-c*m,n[6]=d,n[10]=c*p}else if(e.order==="ZYX"){const g=c*x,y=c*S,M=d*x,C=d*S;n[0]=p*x,n[4]=M*m-y,n[8]=g*m+C,n[1]=p*S,n[5]=C*m+g,n[9]=y*m-M,n[2]=-m,n[6]=d*p,n[10]=c*p}else if(e.order==="YZX"){const g=c*p,y=c*m,M=d*p,C=d*m;n[0]=p*x,n[4]=C-g*S,n[8]=M*S+y,n[1]=S,n[5]=c*x,n[9]=-d*x,n[2]=-m*x,n[6]=y*S+M,n[10]=g-C*S}else if(e.order==="XZY"){const g=c*p,y=c*m,M=d*p,C=d*m;n[0]=p*x,n[4]=-S,n[8]=m*x,n[1]=g*S+C,n[5]=c*x,n[9]=y*S-M,n[2]=M*S-y,n[6]=d*x,n[10]=C*S+g}return n[3]=0,n[7]=0,n[11]=0,n[12]=0,n[13]=0,n[14]=0,n[15]=1,this}makeRotationFromQuaternion(e){return this.compose(Z0,e,Q0)}lookAt(e,n,r){const o=this.elements;return Vn.subVectors(e,n),Vn.lengthSq()===0&&(Vn.z=1),Vn.normalize(),Sr.crossVectors(r,Vn),Sr.lengthSq()===0&&(Math.abs(r.z)===1?Vn.x+=1e-4:Vn.z+=1e-4,Vn.normalize(),Sr.crossVectors(r,Vn)),Sr.normalize(),il.crossVectors(Vn,Sr),o[0]=Sr.x,o[4]=il.x,o[8]=Vn.x,o[1]=Sr.y,o[5]=il.y,o[9]=Vn.y,o[2]=Sr.z,o[6]=il.z,o[10]=Vn.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,n){const r=e.elements,o=n.elements,u=this.elements,c=r[0],d=r[4],p=r[8],m=r[12],x=r[1],S=r[5],g=r[9],y=r[13],M=r[2],C=r[6],_=r[10],v=r[14],R=r[3],L=r[7],b=r[11],F=r[15],U=o[0],z=o[4],A=o[8],D=o[12],fe=o[1],O=o[5],te=o[9],Q=o[13],oe=o[2],K=o[6],ee=o[10],W=o[14],q=o[3],ae=o[7],le=o[11],I=o[15];return u[0]=c*U+d*fe+p*oe+m*q,u[4]=c*z+d*O+p*K+m*ae,u[8]=c*A+d*te+p*ee+m*le,u[12]=c*D+d*Q+p*W+m*I,u[1]=x*U+S*fe+g*oe+y*q,u[5]=x*z+S*O+g*K+y*ae,u[9]=x*A+S*te+g*ee+y*le,u[13]=x*D+S*Q+g*W+y*I,u[2]=M*U+C*fe+_*oe+v*q,u[6]=M*z+C*O+_*K+v*ae,u[10]=M*A+C*te+_*ee+v*le,u[14]=M*D+C*Q+_*W+v*I,u[3]=R*U+L*fe+b*oe+F*q,u[7]=R*z+L*O+b*K+F*ae,u[11]=R*A+L*te+b*ee+F*le,u[15]=R*D+L*Q+b*W+F*I,this}multiplyScalar(e){const n=this.elements;return n[0]*=e,n[4]*=e,n[8]*=e,n[12]*=e,n[1]*=e,n[5]*=e,n[9]*=e,n[13]*=e,n[2]*=e,n[6]*=e,n[10]*=e,n[14]*=e,n[3]*=e,n[7]*=e,n[11]*=e,n[15]*=e,this}determinant(){const e=this.elements,n=e[0],r=e[4],o=e[8],u=e[12],c=e[1],d=e[5],p=e[9],m=e[13],x=e[2],S=e[6],g=e[10],y=e[14],M=e[3],C=e[7],_=e[11],v=e[15],R=p*y-m*g,L=d*y-m*S,b=d*g-p*S,F=c*y-m*x,U=c*g-p*x,z=c*S-d*x;return n*(C*R-_*L+v*b)-r*(M*R-_*F+v*U)+o*(M*L-C*F+v*z)-u*(M*b-C*U+_*z)}transpose(){const e=this.elements;let n;return n=e[1],e[1]=e[4],e[4]=n,n=e[2],e[2]=e[8],e[8]=n,n=e[6],e[6]=e[9],e[9]=n,n=e[3],e[3]=e[12],e[12]=n,n=e[7],e[7]=e[13],e[13]=n,n=e[11],e[11]=e[14],e[14]=n,this}setPosition(e,n,r){const o=this.elements;return e.isVector3?(o[12]=e.x,o[13]=e.y,o[14]=e.z):(o[12]=e,o[13]=n,o[14]=r),this}invert(){const e=this.elements,n=e[0],r=e[1],o=e[2],u=e[3],c=e[4],d=e[5],p=e[6],m=e[7],x=e[8],S=e[9],g=e[10],y=e[11],M=e[12],C=e[13],_=e[14],v=e[15],R=n*d-r*c,L=n*p-o*c,b=n*m-u*c,F=r*p-o*d,U=r*m-u*d,z=o*m-u*p,A=x*C-S*M,D=x*_-g*M,fe=x*v-y*M,O=S*_-g*C,te=S*v-y*C,Q=g*v-y*_,oe=R*Q-L*te+b*O+F*fe-U*D+z*A;if(oe===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const K=1/oe;return e[0]=(d*Q-p*te+m*O)*K,e[1]=(o*te-r*Q-u*O)*K,e[2]=(C*z-_*U+v*F)*K,e[3]=(g*U-S*z-y*F)*K,e[4]=(p*fe-c*Q-m*D)*K,e[5]=(n*Q-o*fe+u*D)*K,e[6]=(_*b-M*z-v*L)*K,e[7]=(x*z-g*b+y*L)*K,e[8]=(c*te-d*fe+m*A)*K,e[9]=(r*fe-n*te-u*A)*K,e[10]=(M*U-C*b+v*R)*K,e[11]=(S*b-x*U-y*R)*K,e[12]=(d*D-c*O-p*A)*K,e[13]=(n*O-r*D+o*A)*K,e[14]=(C*L-M*F-_*R)*K,e[15]=(x*F-S*L+g*R)*K,this}scale(e){const n=this.elements,r=e.x,o=e.y,u=e.z;return n[0]*=r,n[4]*=o,n[8]*=u,n[1]*=r,n[5]*=o,n[9]*=u,n[2]*=r,n[6]*=o,n[10]*=u,n[3]*=r,n[7]*=o,n[11]*=u,this}getMaxScaleOnAxis(){const e=this.elements,n=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],r=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],o=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(n,r,o))}makeTranslation(e,n,r){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,n,0,0,1,r,0,0,0,1),this}makeRotationX(e){const n=Math.cos(e),r=Math.sin(e);return this.set(1,0,0,0,0,n,-r,0,0,r,n,0,0,0,0,1),this}makeRotationY(e){const n=Math.cos(e),r=Math.sin(e);return this.set(n,0,r,0,0,1,0,0,-r,0,n,0,0,0,0,1),this}makeRotationZ(e){const n=Math.cos(e),r=Math.sin(e);return this.set(n,-r,0,0,r,n,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,n){const r=Math.cos(n),o=Math.sin(n),u=1-r,c=e.x,d=e.y,p=e.z,m=u*c,x=u*d;return this.set(m*c+r,m*d-o*p,m*p+o*d,0,m*d+o*p,x*d+r,x*p-o*c,0,m*p-o*d,x*p+o*c,u*p*p+r,0,0,0,0,1),this}makeScale(e,n,r){return this.set(e,0,0,0,0,n,0,0,0,0,r,0,0,0,0,1),this}makeShear(e,n,r,o,u,c){return this.set(1,r,u,0,e,1,c,0,n,o,1,0,0,0,0,1),this}compose(e,n,r){const o=this.elements,u=n._x,c=n._y,d=n._z,p=n._w,m=u+u,x=c+c,S=d+d,g=u*m,y=u*x,M=u*S,C=c*x,_=c*S,v=d*S,R=p*m,L=p*x,b=p*S,F=r.x,U=r.y,z=r.z;return o[0]=(1-(C+v))*F,o[1]=(y+b)*F,o[2]=(M-L)*F,o[3]=0,o[4]=(y-b)*U,o[5]=(1-(g+v))*U,o[6]=(_+R)*U,o[7]=0,o[8]=(M+L)*z,o[9]=(_-R)*z,o[10]=(1-(g+C))*z,o[11]=0,o[12]=e.x,o[13]=e.y,o[14]=e.z,o[15]=1,this}decompose(e,n,r){const o=this.elements;e.x=o[12],e.y=o[13],e.z=o[14];const u=this.determinant();if(u===0)return r.set(1,1,1),n.identity(),this;let c=Rs.set(o[0],o[1],o[2]).length();const d=Rs.set(o[4],o[5],o[6]).length(),p=Rs.set(o[8],o[9],o[10]).length();u<0&&(c=-c),fi.copy(this);const m=1/c,x=1/d,S=1/p;return fi.elements[0]*=m,fi.elements[1]*=m,fi.elements[2]*=m,fi.elements[4]*=x,fi.elements[5]*=x,fi.elements[6]*=x,fi.elements[8]*=S,fi.elements[9]*=S,fi.elements[10]*=S,n.setFromRotationMatrix(fi),r.x=c,r.y=d,r.z=p,this}makePerspective(e,n,r,o,u,c,d=Ci,p=!1){const m=this.elements,x=2*u/(n-e),S=2*u/(r-o),g=(n+e)/(n-e),y=(r+o)/(r-o);let M,C;if(p)M=u/(c-u),C=c*u/(c-u);else if(d===Ci)M=-(c+u)/(c-u),C=-2*c*u/(c-u);else if(d===Il)M=-c/(c-u),C=-c*u/(c-u);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+d);return m[0]=x,m[4]=0,m[8]=g,m[12]=0,m[1]=0,m[5]=S,m[9]=y,m[13]=0,m[2]=0,m[6]=0,m[10]=M,m[14]=C,m[3]=0,m[7]=0,m[11]=-1,m[15]=0,this}makeOrthographic(e,n,r,o,u,c,d=Ci,p=!1){const m=this.elements,x=2/(n-e),S=2/(r-o),g=-(n+e)/(n-e),y=-(r+o)/(r-o);let M,C;if(p)M=1/(c-u),C=c/(c-u);else if(d===Ci)M=-2/(c-u),C=-(c+u)/(c-u);else if(d===Il)M=-1/(c-u),C=-u/(c-u);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+d);return m[0]=x,m[4]=0,m[8]=0,m[12]=g,m[1]=0,m[5]=S,m[9]=0,m[13]=y,m[2]=0,m[6]=0,m[10]=M,m[14]=C,m[3]=0,m[7]=0,m[11]=0,m[15]=1,this}equals(e){const n=this.elements,r=e.elements;for(let o=0;o<16;o++)if(n[o]!==r[o])return!1;return!0}fromArray(e,n=0){for(let r=0;r<16;r++)this.elements[r]=e[r+n];return this}toArray(e=[],n=0){const r=this.elements;return e[n]=r[0],e[n+1]=r[1],e[n+2]=r[2],e[n+3]=r[3],e[n+4]=r[4],e[n+5]=r[5],e[n+6]=r[6],e[n+7]=r[7],e[n+8]=r[8],e[n+9]=r[9],e[n+10]=r[10],e[n+11]=r[11],e[n+12]=r[12],e[n+13]=r[13],e[n+14]=r[14],e[n+15]=r[15],e}}const Rs=new ne,fi=new $t,Z0=new ne(0,0,0),Q0=new ne(1,1,1),Sr=new ne,il=new ne,Vn=new ne,Kp=new $t,Zp=new qs;class Qi{constructor(e=0,n=0,r=0,o=Qi.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=n,this._z=r,this._order=o}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,n,r,o=this._order){return this._x=e,this._y=n,this._z=r,this._order=o,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,n=this._order,r=!0){const o=e.elements,u=o[0],c=o[4],d=o[8],p=o[1],m=o[5],x=o[9],S=o[2],g=o[6],y=o[10];switch(n){case"XYZ":this._y=Math.asin(_t(d,-1,1)),Math.abs(d)<.9999999?(this._x=Math.atan2(-x,y),this._z=Math.atan2(-c,u)):(this._x=Math.atan2(g,m),this._z=0);break;case"YXZ":this._x=Math.asin(-_t(x,-1,1)),Math.abs(x)<.9999999?(this._y=Math.atan2(d,y),this._z=Math.atan2(p,m)):(this._y=Math.atan2(-S,u),this._z=0);break;case"ZXY":this._x=Math.asin(_t(g,-1,1)),Math.abs(g)<.9999999?(this._y=Math.atan2(-S,y),this._z=Math.atan2(-c,m)):(this._y=0,this._z=Math.atan2(p,u));break;case"ZYX":this._y=Math.asin(-_t(S,-1,1)),Math.abs(S)<.9999999?(this._x=Math.atan2(g,y),this._z=Math.atan2(p,u)):(this._x=0,this._z=Math.atan2(-c,m));break;case"YZX":this._z=Math.asin(_t(p,-1,1)),Math.abs(p)<.9999999?(this._x=Math.atan2(-x,m),this._y=Math.atan2(-S,u)):(this._x=0,this._y=Math.atan2(d,y));break;case"XZY":this._z=Math.asin(-_t(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(g,m),this._y=Math.atan2(d,u)):(this._x=Math.atan2(-x,y),this._y=0);break;default:ot("Euler: .setFromRotationMatrix() encountered an unknown order: "+n)}return this._order=n,r===!0&&this._onChangeCallback(),this}setFromQuaternion(e,n,r){return Kp.makeRotationFromQuaternion(e),this.setFromRotationMatrix(Kp,n,r)}setFromVector3(e,n=this._order){return this.set(e.x,e.y,e.z,n)}reorder(e){return Zp.setFromEuler(this),this.setFromQuaternion(Zp,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],n=0){return e[n]=this._x,e[n+1]=this._y,e[n+2]=this._z,e[n+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}Qi.DEFAULT_ORDER="XYZ";class eg{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}}let J0=0;const Qp=new ne,bs=new qs,Hi=new $t,rl=new ne,Da=new ne,ev=new ne,tv=new qs,Jp=new ne(1,0,0),em=new ne(0,1,0),tm=new ne(0,0,1),nm={type:"added"},nv={type:"removed"},Ps={type:"childadded",child:null},Uc={type:"childremoved",child:null};class Un extends Ys{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:J0++}),this.uuid=Ga(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=Un.DEFAULT_UP.clone();const e=new ne,n=new Qi,r=new qs,o=new ne(1,1,1);function u(){r.setFromEuler(n,!1)}function c(){n.setFromQuaternion(r,void 0,!1)}n._onChange(u),r._onChange(c),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:n},quaternion:{configurable:!0,enumerable:!0,value:r},scale:{configurable:!0,enumerable:!0,value:o},modelViewMatrix:{value:new $t},normalMatrix:{value:new ft}}),this.matrix=new $t,this.matrixWorld=new $t,this.matrixAutoUpdate=Un.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=Un.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new eg,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.static=!1,this.userData={},this.pivot=null}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,n){this.quaternion.setFromAxisAngle(e,n)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,n){return bs.setFromAxisAngle(e,n),this.quaternion.multiply(bs),this}rotateOnWorldAxis(e,n){return bs.setFromAxisAngle(e,n),this.quaternion.premultiply(bs),this}rotateX(e){return this.rotateOnAxis(Jp,e)}rotateY(e){return this.rotateOnAxis(em,e)}rotateZ(e){return this.rotateOnAxis(tm,e)}translateOnAxis(e,n){return Qp.copy(e).applyQuaternion(this.quaternion),this.position.add(Qp.multiplyScalar(n)),this}translateX(e){return this.translateOnAxis(Jp,e)}translateY(e){return this.translateOnAxis(em,e)}translateZ(e){return this.translateOnAxis(tm,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(Hi.copy(this.matrixWorld).invert())}lookAt(e,n,r){e.isVector3?rl.copy(e):rl.set(e,n,r);const o=this.parent;this.updateWorldMatrix(!0,!1),Da.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Hi.lookAt(Da,rl,this.up):Hi.lookAt(rl,Da,this.up),this.quaternion.setFromRotationMatrix(Hi),o&&(Hi.extractRotation(o.matrixWorld),bs.setFromRotationMatrix(Hi),this.quaternion.premultiply(bs.invert()))}add(e){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.add(arguments[n]);return this}return e===this?(wt("Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.removeFromParent(),e.parent=this,this.children.push(e),e.dispatchEvent(nm),Ps.child=e,this.dispatchEvent(Ps),Ps.child=null):wt("Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let r=0;r<arguments.length;r++)this.remove(arguments[r]);return this}const n=this.children.indexOf(e);return n!==-1&&(e.parent=null,this.children.splice(n,1),e.dispatchEvent(nv),Uc.child=e,this.dispatchEvent(Uc),Uc.child=null),this}removeFromParent(){const e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),Hi.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),Hi.multiply(e.parent.matrixWorld)),e.applyMatrix4(Hi),e.removeFromParent(),e.parent=this,this.children.push(e),e.updateWorldMatrix(!1,!0),e.dispatchEvent(nm),Ps.child=e,this.dispatchEvent(Ps),Ps.child=null,this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,n){if(this[e]===n)return this;for(let r=0,o=this.children.length;r<o;r++){const c=this.children[r].getObjectByProperty(e,n);if(c!==void 0)return c}}getObjectsByProperty(e,n,r=[]){this[e]===n&&r.push(this);const o=this.children;for(let u=0,c=o.length;u<c;u++)o[u].getObjectsByProperty(e,n,r);return r}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Da,e,ev),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Da,tv,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);const n=this.matrixWorld.elements;return e.set(n[8],n[9],n[10]).normalize()}raycast(){}traverse(e){e(this);const n=this.children;for(let r=0,o=n.length;r<o;r++)n[r].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);const n=this.children;for(let r=0,o=n.length;r<o;r++)n[r].traverseVisible(e)}traverseAncestors(e){const n=this.parent;n!==null&&(e(n),n.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale);const e=this.pivot;if(e!==null){const n=e.x,r=e.y,o=e.z,u=this.matrix.elements;u[12]+=n-u[0]*n-u[4]*r-u[8]*o,u[13]+=r-u[1]*n-u[5]*r-u[9]*o,u[14]+=o-u[2]*n-u[6]*r-u[10]*o}this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,e=!0);const n=this.children;for(let r=0,o=n.length;r<o;r++)n[r].updateMatrixWorld(e)}updateWorldMatrix(e,n){const r=this.parent;if(e===!0&&r!==null&&r.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),n===!0){const o=this.children;for(let u=0,c=o.length;u<c;u++)o[u].updateWorldMatrix(!1,!0)}}toJSON(e){const n=e===void 0||typeof e=="string",r={};n&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},r.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});const o={};o.uuid=this.uuid,o.type=this.type,this.name!==""&&(o.name=this.name),this.castShadow===!0&&(o.castShadow=!0),this.receiveShadow===!0&&(o.receiveShadow=!0),this.visible===!1&&(o.visible=!1),this.frustumCulled===!1&&(o.frustumCulled=!1),this.renderOrder!==0&&(o.renderOrder=this.renderOrder),this.static!==!1&&(o.static=this.static),Object.keys(this.userData).length>0&&(o.userData=this.userData),o.layers=this.layers.mask,o.matrix=this.matrix.toArray(),o.up=this.up.toArray(),this.pivot!==null&&(o.pivot=this.pivot.toArray()),this.matrixAutoUpdate===!1&&(o.matrixAutoUpdate=!1),this.morphTargetDictionary!==void 0&&(o.morphTargetDictionary=Object.assign({},this.morphTargetDictionary)),this.morphTargetInfluences!==void 0&&(o.morphTargetInfluences=this.morphTargetInfluences.slice()),this.isInstancedMesh&&(o.type="InstancedMesh",o.count=this.count,o.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(o.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(o.type="BatchedMesh",o.perObjectFrustumCulled=this.perObjectFrustumCulled,o.sortObjects=this.sortObjects,o.drawRanges=this._drawRanges,o.reservedRanges=this._reservedRanges,o.geometryInfo=this._geometryInfo.map(d=>({...d,boundingBox:d.boundingBox?d.boundingBox.toJSON():void 0,boundingSphere:d.boundingSphere?d.boundingSphere.toJSON():void 0})),o.instanceInfo=this._instanceInfo.map(d=>({...d})),o.availableInstanceIds=this._availableInstanceIds.slice(),o.availableGeometryIds=this._availableGeometryIds.slice(),o.nextIndexStart=this._nextIndexStart,o.nextVertexStart=this._nextVertexStart,o.geometryCount=this._geometryCount,o.maxInstanceCount=this._maxInstanceCount,o.maxVertexCount=this._maxVertexCount,o.maxIndexCount=this._maxIndexCount,o.geometryInitialized=this._geometryInitialized,o.matricesTexture=this._matricesTexture.toJSON(e),o.indirectTexture=this._indirectTexture.toJSON(e),this._colorsTexture!==null&&(o.colorsTexture=this._colorsTexture.toJSON(e)),this.boundingSphere!==null&&(o.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(o.boundingBox=this.boundingBox.toJSON()));function u(d,p){return d[p.uuid]===void 0&&(d[p.uuid]=p.toJSON(e)),p.uuid}if(this.isScene)this.background&&(this.background.isColor?o.background=this.background.toJSON():this.background.isTexture&&(o.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(o.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){o.geometry=u(e.geometries,this.geometry);const d=this.geometry.parameters;if(d!==void 0&&d.shapes!==void 0){const p=d.shapes;if(Array.isArray(p))for(let m=0,x=p.length;m<x;m++){const S=p[m];u(e.shapes,S)}else u(e.shapes,p)}}if(this.isSkinnedMesh&&(o.bindMode=this.bindMode,o.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(u(e.skeletons,this.skeleton),o.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const d=[];for(let p=0,m=this.material.length;p<m;p++)d.push(u(e.materials,this.material[p]));o.material=d}else o.material=u(e.materials,this.material);if(this.children.length>0){o.children=[];for(let d=0;d<this.children.length;d++)o.children.push(this.children[d].toJSON(e).object)}if(this.animations.length>0){o.animations=[];for(let d=0;d<this.animations.length;d++){const p=this.animations[d];o.animations.push(u(e.animations,p))}}if(n){const d=c(e.geometries),p=c(e.materials),m=c(e.textures),x=c(e.images),S=c(e.shapes),g=c(e.skeletons),y=c(e.animations),M=c(e.nodes);d.length>0&&(r.geometries=d),p.length>0&&(r.materials=p),m.length>0&&(r.textures=m),x.length>0&&(r.images=x),S.length>0&&(r.shapes=S),g.length>0&&(r.skeletons=g),y.length>0&&(r.animations=y),M.length>0&&(r.nodes=M)}return r.object=o,r;function c(d){const p=[];for(const m in d){const x=d[m];delete x.metadata,p.push(x)}return p}}clone(e){return new this.constructor().copy(this,e)}copy(e,n=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),e.pivot!==null&&(this.pivot=e.pivot.clone()),this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.static=e.static,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),n===!0)for(let r=0;r<e.children.length;r++){const o=e.children[r];this.add(o.clone())}return this}}Un.DEFAULT_UP=new ne(0,1,0);Un.DEFAULT_MATRIX_AUTO_UPDATE=!0;Un.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;class sl extends Un{constructor(){super(),this.isGroup=!0,this.type="Group"}}const iv={type:"move"};class Fc{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new sl,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new sl,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new ne,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new ne),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new sl,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new ne,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new ne),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){const n=this._hand;if(n)for(const r of e.hand.values())this._getHandJoint(n,r)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,n,r){let o=null,u=null,c=null;const d=this._targetRay,p=this._grip,m=this._hand;if(e&&n.session.visibilityState!=="visible-blurred"){if(m&&e.hand){c=!0;for(const C of e.hand.values()){const _=n.getJointPose(C,r),v=this._getHandJoint(m,C);_!==null&&(v.matrix.fromArray(_.transform.matrix),v.matrix.decompose(v.position,v.rotation,v.scale),v.matrixWorldNeedsUpdate=!0,v.jointRadius=_.radius),v.visible=_!==null}const x=m.joints["index-finger-tip"],S=m.joints["thumb-tip"],g=x.position.distanceTo(S.position),y=.02,M=.005;m.inputState.pinching&&g>y+M?(m.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!m.inputState.pinching&&g<=y-M&&(m.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else p!==null&&e.gripSpace&&(u=n.getPose(e.gripSpace,r),u!==null&&(p.matrix.fromArray(u.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,u.linearVelocity?(p.hasLinearVelocity=!0,p.linearVelocity.copy(u.linearVelocity)):p.hasLinearVelocity=!1,u.angularVelocity?(p.hasAngularVelocity=!0,p.angularVelocity.copy(u.angularVelocity)):p.hasAngularVelocity=!1));d!==null&&(o=n.getPose(e.targetRaySpace,r),o===null&&u!==null&&(o=u),o!==null&&(d.matrix.fromArray(o.transform.matrix),d.matrix.decompose(d.position,d.rotation,d.scale),d.matrixWorldNeedsUpdate=!0,o.linearVelocity?(d.hasLinearVelocity=!0,d.linearVelocity.copy(o.linearVelocity)):d.hasLinearVelocity=!1,o.angularVelocity?(d.hasAngularVelocity=!0,d.angularVelocity.copy(o.angularVelocity)):d.hasAngularVelocity=!1,this.dispatchEvent(iv)))}return d!==null&&(d.visible=o!==null),p!==null&&(p.visible=u!==null),m!==null&&(m.visible=c!==null),this}_getHandJoint(e,n){if(e.joints[n.jointName]===void 0){const r=new sl;r.matrixAutoUpdate=!1,r.visible=!1,e.joints[n.jointName]=r,e.add(r)}return e.joints[n.jointName]}}const tg={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},yr={h:0,s:0,l:0},al={h:0,s:0,l:0};function Oc(s,e,n){return n<0&&(n+=1),n>1&&(n-=1),n<1/6?s+(e-s)*6*n:n<1/2?e:n<2/3?s+(e-s)*6*(2/3-n):s}class bt{constructor(e,n,r){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,n,r)}set(e,n,r){if(n===void 0&&r===void 0){const o=e;o&&o.isColor?this.copy(o):typeof o=="number"?this.setHex(o):typeof o=="string"&&this.setStyle(o)}else this.setRGB(e,n,r);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,n=ei){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,Et.colorSpaceToWorking(this,n),this}setRGB(e,n,r,o=Et.workingColorSpace){return this.r=e,this.g=n,this.b=r,Et.colorSpaceToWorking(this,o),this}setHSL(e,n,r,o=Et.workingColorSpace){if(e=W0(e,1),n=_t(n,0,1),r=_t(r,0,1),n===0)this.r=this.g=this.b=r;else{const u=r<=.5?r*(1+n):r+n-r*n,c=2*r-u;this.r=Oc(c,u,e+1/3),this.g=Oc(c,u,e),this.b=Oc(c,u,e-1/3)}return Et.colorSpaceToWorking(this,o),this}setStyle(e,n=ei){function r(u){u!==void 0&&parseFloat(u)<1&&ot("Color: Alpha component of "+e+" will be ignored.")}let o;if(o=/^(\w+)\(([^\)]*)\)/.exec(e)){let u;const c=o[1],d=o[2];switch(c){case"rgb":case"rgba":if(u=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(d))return r(u[4]),this.setRGB(Math.min(255,parseInt(u[1],10))/255,Math.min(255,parseInt(u[2],10))/255,Math.min(255,parseInt(u[3],10))/255,n);if(u=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(d))return r(u[4]),this.setRGB(Math.min(100,parseInt(u[1],10))/100,Math.min(100,parseInt(u[2],10))/100,Math.min(100,parseInt(u[3],10))/100,n);break;case"hsl":case"hsla":if(u=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(d))return r(u[4]),this.setHSL(parseFloat(u[1])/360,parseFloat(u[2])/100,parseFloat(u[3])/100,n);break;default:ot("Color: Unknown color model "+e)}}else if(o=/^\#([A-Fa-f\d]+)$/.exec(e)){const u=o[1],c=u.length;if(c===3)return this.setRGB(parseInt(u.charAt(0),16)/15,parseInt(u.charAt(1),16)/15,parseInt(u.charAt(2),16)/15,n);if(c===6)return this.setHex(parseInt(u,16),n);ot("Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,n);return this}setColorName(e,n=ei){const r=tg[e.toLowerCase()];return r!==void 0?this.setHex(r,n):ot("Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=$i(e.r),this.g=$i(e.g),this.b=$i(e.b),this}copyLinearToSRGB(e){return this.r=Vs(e.r),this.g=Vs(e.g),this.b=Vs(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=ei){return Et.workingToColorSpace(gn.copy(this),e),Math.round(_t(gn.r*255,0,255))*65536+Math.round(_t(gn.g*255,0,255))*256+Math.round(_t(gn.b*255,0,255))}getHexString(e=ei){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,n=Et.workingColorSpace){Et.workingToColorSpace(gn.copy(this),n);const r=gn.r,o=gn.g,u=gn.b,c=Math.max(r,o,u),d=Math.min(r,o,u);let p,m;const x=(d+c)/2;if(d===c)p=0,m=0;else{const S=c-d;switch(m=x<=.5?S/(c+d):S/(2-c-d),c){case r:p=(o-u)/S+(o<u?6:0);break;case o:p=(u-r)/S+2;break;case u:p=(r-o)/S+4;break}p/=6}return e.h=p,e.s=m,e.l=x,e}getRGB(e,n=Et.workingColorSpace){return Et.workingToColorSpace(gn.copy(this),n),e.r=gn.r,e.g=gn.g,e.b=gn.b,e}getStyle(e=ei){Et.workingToColorSpace(gn.copy(this),e);const n=gn.r,r=gn.g,o=gn.b;return e!==ei?`color(${e} ${n.toFixed(3)} ${r.toFixed(3)} ${o.toFixed(3)})`:`rgb(${Math.round(n*255)},${Math.round(r*255)},${Math.round(o*255)})`}offsetHSL(e,n,r){return this.getHSL(yr),this.setHSL(yr.h+e,yr.s+n,yr.l+r)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,n){return this.r=e.r+n.r,this.g=e.g+n.g,this.b=e.b+n.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,n){return this.r+=(e.r-this.r)*n,this.g+=(e.g-this.g)*n,this.b+=(e.b-this.b)*n,this}lerpColors(e,n,r){return this.r=e.r+(n.r-e.r)*r,this.g=e.g+(n.g-e.g)*r,this.b=e.b+(n.b-e.b)*r,this}lerpHSL(e,n){this.getHSL(yr),e.getHSL(al);const r=Pc(yr.h,al.h,n),o=Pc(yr.s,al.s,n),u=Pc(yr.l,al.l,n);return this.setHSL(r,o,u),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){const n=this.r,r=this.g,o=this.b,u=e.elements;return this.r=u[0]*n+u[3]*r+u[6]*o,this.g=u[1]*n+u[4]*r+u[7]*o,this.b=u[2]*n+u[5]*r+u[8]*o,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,n=0){return this.r=e[n],this.g=e[n+1],this.b=e[n+2],this}toArray(e=[],n=0){return e[n]=this.r,e[n+1]=this.g,e[n+2]=this.b,e}fromBufferAttribute(e,n){return this.r=e.getX(n),this.g=e.getY(n),this.b=e.getZ(n),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const gn=new bt;bt.NAMES=tg;class rv extends Un{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new Qi,this.environmentIntensity=1,this.environmentRotation=new Qi,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,n){return super.copy(e,n),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){const n=super.toJSON(e);return this.fog!==null&&(n.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(n.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(n.object.backgroundIntensity=this.backgroundIntensity),n.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(n.object.environmentIntensity=this.environmentIntensity),n.object.environmentRotation=this.environmentRotation.toArray(),n}}const di=new ne,Gi=new ne,Bc=new ne,Wi=new ne,Ds=new ne,Ls=new ne,im=new ne,kc=new ne,zc=new ne,Vc=new ne,Hc=new qt,Gc=new qt,Wc=new qt;class pi{constructor(e=new ne,n=new ne,r=new ne){this.a=e,this.b=n,this.c=r}static getNormal(e,n,r,o){o.subVectors(r,n),di.subVectors(e,n),o.cross(di);const u=o.lengthSq();return u>0?o.multiplyScalar(1/Math.sqrt(u)):o.set(0,0,0)}static getBarycoord(e,n,r,o,u){di.subVectors(o,n),Gi.subVectors(r,n),Bc.subVectors(e,n);const c=di.dot(di),d=di.dot(Gi),p=di.dot(Bc),m=Gi.dot(Gi),x=Gi.dot(Bc),S=c*m-d*d;if(S===0)return u.set(0,0,0),null;const g=1/S,y=(m*p-d*x)*g,M=(c*x-d*p)*g;return u.set(1-y-M,M,y)}static containsPoint(e,n,r,o){return this.getBarycoord(e,n,r,o,Wi)===null?!1:Wi.x>=0&&Wi.y>=0&&Wi.x+Wi.y<=1}static getInterpolation(e,n,r,o,u,c,d,p){return this.getBarycoord(e,n,r,o,Wi)===null?(p.x=0,p.y=0,"z"in p&&(p.z=0),"w"in p&&(p.w=0),null):(p.setScalar(0),p.addScaledVector(u,Wi.x),p.addScaledVector(c,Wi.y),p.addScaledVector(d,Wi.z),p)}static getInterpolatedAttribute(e,n,r,o,u,c){return Hc.setScalar(0),Gc.setScalar(0),Wc.setScalar(0),Hc.fromBufferAttribute(e,n),Gc.fromBufferAttribute(e,r),Wc.fromBufferAttribute(e,o),c.setScalar(0),c.addScaledVector(Hc,u.x),c.addScaledVector(Gc,u.y),c.addScaledVector(Wc,u.z),c}static isFrontFacing(e,n,r,o){return di.subVectors(r,n),Gi.subVectors(e,n),di.cross(Gi).dot(o)<0}set(e,n,r){return this.a.copy(e),this.b.copy(n),this.c.copy(r),this}setFromPointsAndIndices(e,n,r,o){return this.a.copy(e[n]),this.b.copy(e[r]),this.c.copy(e[o]),this}setFromAttributeAndIndices(e,n,r,o){return this.a.fromBufferAttribute(e,n),this.b.fromBufferAttribute(e,r),this.c.fromBufferAttribute(e,o),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return di.subVectors(this.c,this.b),Gi.subVectors(this.a,this.b),di.cross(Gi).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return pi.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,n){return pi.getBarycoord(e,this.a,this.b,this.c,n)}getInterpolation(e,n,r,o,u){return pi.getInterpolation(e,this.a,this.b,this.c,n,r,o,u)}containsPoint(e){return pi.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return pi.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,n){const r=this.a,o=this.b,u=this.c;let c,d;Ds.subVectors(o,r),Ls.subVectors(u,r),kc.subVectors(e,r);const p=Ds.dot(kc),m=Ls.dot(kc);if(p<=0&&m<=0)return n.copy(r);zc.subVectors(e,o);const x=Ds.dot(zc),S=Ls.dot(zc);if(x>=0&&S<=x)return n.copy(o);const g=p*S-x*m;if(g<=0&&p>=0&&x<=0)return c=p/(p-x),n.copy(r).addScaledVector(Ds,c);Vc.subVectors(e,u);const y=Ds.dot(Vc),M=Ls.dot(Vc);if(M>=0&&y<=M)return n.copy(u);const C=y*m-p*M;if(C<=0&&m>=0&&M<=0)return d=m/(m-M),n.copy(r).addScaledVector(Ls,d);const _=x*M-y*S;if(_<=0&&S-x>=0&&y-M>=0)return im.subVectors(u,o),d=(S-x)/(S-x+(y-M)),n.copy(o).addScaledVector(im,d);const v=1/(_+C+g);return c=C*v,d=g*v,n.copy(r).addScaledVector(Ds,c).addScaledVector(Ls,d)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}}class Wa{constructor(e=new ne(1/0,1/0,1/0),n=new ne(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=n}set(e,n){return this.min.copy(e),this.max.copy(n),this}setFromArray(e){this.makeEmpty();for(let n=0,r=e.length;n<r;n+=3)this.expandByPoint(hi.fromArray(e,n));return this}setFromBufferAttribute(e){this.makeEmpty();for(let n=0,r=e.count;n<r;n++)this.expandByPoint(hi.fromBufferAttribute(e,n));return this}setFromPoints(e){this.makeEmpty();for(let n=0,r=e.length;n<r;n++)this.expandByPoint(e[n]);return this}setFromCenterAndSize(e,n){const r=hi.copy(n).multiplyScalar(.5);return this.min.copy(e).sub(r),this.max.copy(e).add(r),this}setFromObject(e,n=!1){return this.makeEmpty(),this.expandByObject(e,n)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,n=!1){e.updateWorldMatrix(!1,!1);const r=e.geometry;if(r!==void 0){const u=r.getAttribute("position");if(n===!0&&u!==void 0&&e.isInstancedMesh!==!0)for(let c=0,d=u.count;c<d;c++)e.isMesh===!0?e.getVertexPosition(c,hi):hi.fromBufferAttribute(u,c),hi.applyMatrix4(e.matrixWorld),this.expandByPoint(hi);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),ol.copy(e.boundingBox)):(r.boundingBox===null&&r.computeBoundingBox(),ol.copy(r.boundingBox)),ol.applyMatrix4(e.matrixWorld),this.union(ol)}const o=e.children;for(let u=0,c=o.length;u<c;u++)this.expandByObject(o[u],n);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,n){return n.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,hi),hi.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let n,r;return e.normal.x>0?(n=e.normal.x*this.min.x,r=e.normal.x*this.max.x):(n=e.normal.x*this.max.x,r=e.normal.x*this.min.x),e.normal.y>0?(n+=e.normal.y*this.min.y,r+=e.normal.y*this.max.y):(n+=e.normal.y*this.max.y,r+=e.normal.y*this.min.y),e.normal.z>0?(n+=e.normal.z*this.min.z,r+=e.normal.z*this.max.z):(n+=e.normal.z*this.max.z,r+=e.normal.z*this.min.z),n<=-e.constant&&r>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(La),ll.subVectors(this.max,La),Ns.subVectors(e.a,La),Is.subVectors(e.b,La),Us.subVectors(e.c,La),Mr.subVectors(Is,Ns),Er.subVectors(Us,Is),Wr.subVectors(Ns,Us);let n=[0,-Mr.z,Mr.y,0,-Er.z,Er.y,0,-Wr.z,Wr.y,Mr.z,0,-Mr.x,Er.z,0,-Er.x,Wr.z,0,-Wr.x,-Mr.y,Mr.x,0,-Er.y,Er.x,0,-Wr.y,Wr.x,0];return!Xc(n,Ns,Is,Us,ll)||(n=[1,0,0,0,1,0,0,0,1],!Xc(n,Ns,Is,Us,ll))?!1:(ul.crossVectors(Mr,Er),n=[ul.x,ul.y,ul.z],Xc(n,Ns,Is,Us,ll))}clampPoint(e,n){return n.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,hi).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(hi).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(Xi[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),Xi[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),Xi[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),Xi[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),Xi[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),Xi[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),Xi[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),Xi[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(Xi),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}}const Xi=[new ne,new ne,new ne,new ne,new ne,new ne,new ne,new ne],hi=new ne,ol=new Wa,Ns=new ne,Is=new ne,Us=new ne,Mr=new ne,Er=new ne,Wr=new ne,La=new ne,ll=new ne,ul=new ne,Xr=new ne;function Xc(s,e,n,r,o){for(let u=0,c=s.length-3;u<=c;u+=3){Xr.fromArray(s,u);const d=o.x*Math.abs(Xr.x)+o.y*Math.abs(Xr.y)+o.z*Math.abs(Xr.z),p=e.dot(Xr),m=n.dot(Xr),x=r.dot(Xr);if(Math.max(-Math.max(p,m,x),Math.min(p,m,x))>d)return!1}return!0}const Zt=new ne,cl=new Lt;let sv=0;class gi{constructor(e,n,r=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:sv++}),this.name="",this.array=e,this.itemSize=n,this.count=e!==void 0?e.length/n:0,this.normalized=r,this.usage=Gp,this.updateRanges=[],this.gpuType=Ai,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,n){this.updateRanges.push({start:e,count:n})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,n,r){e*=this.itemSize,r*=n.itemSize;for(let o=0,u=this.itemSize;o<u;o++)this.array[e+o]=n.array[r+o];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let n=0,r=this.count;n<r;n++)cl.fromBufferAttribute(this,n),cl.applyMatrix3(e),this.setXY(n,cl.x,cl.y);else if(this.itemSize===3)for(let n=0,r=this.count;n<r;n++)Zt.fromBufferAttribute(this,n),Zt.applyMatrix3(e),this.setXYZ(n,Zt.x,Zt.y,Zt.z);return this}applyMatrix4(e){for(let n=0,r=this.count;n<r;n++)Zt.fromBufferAttribute(this,n),Zt.applyMatrix4(e),this.setXYZ(n,Zt.x,Zt.y,Zt.z);return this}applyNormalMatrix(e){for(let n=0,r=this.count;n<r;n++)Zt.fromBufferAttribute(this,n),Zt.applyNormalMatrix(e),this.setXYZ(n,Zt.x,Zt.y,Zt.z);return this}transformDirection(e){for(let n=0,r=this.count;n<r;n++)Zt.fromBufferAttribute(this,n),Zt.transformDirection(e),this.setXYZ(n,Zt.x,Zt.y,Zt.z);return this}set(e,n=0){return this.array.set(e,n),this}getComponent(e,n){let r=this.array[e*this.itemSize+n];return this.normalized&&(r=Pa(r,this.array)),r}setComponent(e,n,r){return this.normalized&&(r=Nn(r,this.array)),this.array[e*this.itemSize+n]=r,this}getX(e){let n=this.array[e*this.itemSize];return this.normalized&&(n=Pa(n,this.array)),n}setX(e,n){return this.normalized&&(n=Nn(n,this.array)),this.array[e*this.itemSize]=n,this}getY(e){let n=this.array[e*this.itemSize+1];return this.normalized&&(n=Pa(n,this.array)),n}setY(e,n){return this.normalized&&(n=Nn(n,this.array)),this.array[e*this.itemSize+1]=n,this}getZ(e){let n=this.array[e*this.itemSize+2];return this.normalized&&(n=Pa(n,this.array)),n}setZ(e,n){return this.normalized&&(n=Nn(n,this.array)),this.array[e*this.itemSize+2]=n,this}getW(e){let n=this.array[e*this.itemSize+3];return this.normalized&&(n=Pa(n,this.array)),n}setW(e,n){return this.normalized&&(n=Nn(n,this.array)),this.array[e*this.itemSize+3]=n,this}setXY(e,n,r){return e*=this.itemSize,this.normalized&&(n=Nn(n,this.array),r=Nn(r,this.array)),this.array[e+0]=n,this.array[e+1]=r,this}setXYZ(e,n,r,o){return e*=this.itemSize,this.normalized&&(n=Nn(n,this.array),r=Nn(r,this.array),o=Nn(o,this.array)),this.array[e+0]=n,this.array[e+1]=r,this.array[e+2]=o,this}setXYZW(e,n,r,o,u){return e*=this.itemSize,this.normalized&&(n=Nn(n,this.array),r=Nn(r,this.array),o=Nn(o,this.array),u=Nn(u,this.array)),this.array[e+0]=n,this.array[e+1]=r,this.array[e+2]=o,this.array[e+3]=u,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==Gp&&(e.usage=this.usage),e}}class ng extends gi{constructor(e,n,r){super(new Uint16Array(e),n,r)}}class ig extends gi{constructor(e,n,r){super(new Uint32Array(e),n,r)}}class Tn extends gi{constructor(e,n,r){super(new Float32Array(e),n,r)}}const av=new Wa,Na=new ne,jc=new ne;class kl{constructor(e=new ne,n=-1){this.isSphere=!0,this.center=e,this.radius=n}set(e,n){return this.center.copy(e),this.radius=n,this}setFromPoints(e,n){const r=this.center;n!==void 0?r.copy(n):av.setFromPoints(e).getCenter(r);let o=0;for(let u=0,c=e.length;u<c;u++)o=Math.max(o,r.distanceToSquared(e[u]));return this.radius=Math.sqrt(o),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){const n=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=n*n}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,n){const r=this.center.distanceToSquared(e);return n.copy(e),r>this.radius*this.radius&&(n.sub(this.center).normalize(),n.multiplyScalar(this.radius).add(this.center)),n}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;Na.subVectors(e,this.center);const n=Na.lengthSq();if(n>this.radius*this.radius){const r=Math.sqrt(n),o=(r-this.radius)*.5;this.center.addScaledVector(Na,o/r),this.radius+=o}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(jc.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(Na.copy(e.center).add(jc)),this.expandByPoint(Na.copy(e.center).sub(jc))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}}let ov=0;const Jn=new $t,Yc=new Un,Fs=new ne,Hn=new Wa,Ia=new Wa,on=new ne;class Gn extends Ys{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:ov++}),this.uuid=Ga(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.indirectOffset=0,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(z0(e)?ig:ng)(e,1):this.index=e,this}setIndirect(e,n=0){return this.indirect=e,this.indirectOffset=n,this}getIndirect(){return this.indirect}getAttribute(e){return this.attributes[e]}setAttribute(e,n){return this.attributes[e]=n,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,n,r=0){this.groups.push({start:e,count:n,materialIndex:r})}clearGroups(){this.groups=[]}setDrawRange(e,n){this.drawRange.start=e,this.drawRange.count=n}applyMatrix4(e){const n=this.attributes.position;n!==void 0&&(n.applyMatrix4(e),n.needsUpdate=!0);const r=this.attributes.normal;if(r!==void 0){const u=new ft().getNormalMatrix(e);r.applyNormalMatrix(u),r.needsUpdate=!0}const o=this.attributes.tangent;return o!==void 0&&(o.transformDirection(e),o.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(e){return Jn.makeRotationFromQuaternion(e),this.applyMatrix4(Jn),this}rotateX(e){return Jn.makeRotationX(e),this.applyMatrix4(Jn),this}rotateY(e){return Jn.makeRotationY(e),this.applyMatrix4(Jn),this}rotateZ(e){return Jn.makeRotationZ(e),this.applyMatrix4(Jn),this}translate(e,n,r){return Jn.makeTranslation(e,n,r),this.applyMatrix4(Jn),this}scale(e,n,r){return Jn.makeScale(e,n,r),this.applyMatrix4(Jn),this}lookAt(e){return Yc.lookAt(e),Yc.updateMatrix(),this.applyMatrix4(Yc.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(Fs).negate(),this.translate(Fs.x,Fs.y,Fs.z),this}setFromPoints(e){const n=this.getAttribute("position");if(n===void 0){const r=[];for(let o=0,u=e.length;o<u;o++){const c=e[o];r.push(c.x,c.y,c.z||0)}this.setAttribute("position",new Tn(r,3))}else{const r=Math.min(e.length,n.count);for(let o=0;o<r;o++){const u=e[o];n.setXYZ(o,u.x,u.y,u.z||0)}e.length>n.count&&ot("BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),n.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Wa);const e=this.attributes.position,n=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){wt("BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new ne(-1/0,-1/0,-1/0),new ne(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),n)for(let r=0,o=n.length;r<o;r++){const u=n[r];Hn.setFromBufferAttribute(u),this.morphTargetsRelative?(on.addVectors(this.boundingBox.min,Hn.min),this.boundingBox.expandByPoint(on),on.addVectors(this.boundingBox.max,Hn.max),this.boundingBox.expandByPoint(on)):(this.boundingBox.expandByPoint(Hn.min),this.boundingBox.expandByPoint(Hn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&wt('BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new kl);const e=this.attributes.position,n=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){wt("BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new ne,1/0);return}if(e){const r=this.boundingSphere.center;if(Hn.setFromBufferAttribute(e),n)for(let u=0,c=n.length;u<c;u++){const d=n[u];Ia.setFromBufferAttribute(d),this.morphTargetsRelative?(on.addVectors(Hn.min,Ia.min),Hn.expandByPoint(on),on.addVectors(Hn.max,Ia.max),Hn.expandByPoint(on)):(Hn.expandByPoint(Ia.min),Hn.expandByPoint(Ia.max))}Hn.getCenter(r);let o=0;for(let u=0,c=e.count;u<c;u++)on.fromBufferAttribute(e,u),o=Math.max(o,r.distanceToSquared(on));if(n)for(let u=0,c=n.length;u<c;u++){const d=n[u],p=this.morphTargetsRelative;for(let m=0,x=d.count;m<x;m++)on.fromBufferAttribute(d,m),p&&(Fs.fromBufferAttribute(e,m),on.add(Fs)),o=Math.max(o,r.distanceToSquared(on))}this.boundingSphere.radius=Math.sqrt(o),isNaN(this.boundingSphere.radius)&&wt('BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const e=this.index,n=this.attributes;if(e===null||n.position===void 0||n.normal===void 0||n.uv===void 0){wt("BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const r=n.position,o=n.normal,u=n.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new gi(new Float32Array(4*r.count),4));const c=this.getAttribute("tangent"),d=[],p=[];for(let A=0;A<r.count;A++)d[A]=new ne,p[A]=new ne;const m=new ne,x=new ne,S=new ne,g=new Lt,y=new Lt,M=new Lt,C=new ne,_=new ne;function v(A,D,fe){m.fromBufferAttribute(r,A),x.fromBufferAttribute(r,D),S.fromBufferAttribute(r,fe),g.fromBufferAttribute(u,A),y.fromBufferAttribute(u,D),M.fromBufferAttribute(u,fe),x.sub(m),S.sub(m),y.sub(g),M.sub(g);const O=1/(y.x*M.y-M.x*y.y);isFinite(O)&&(C.copy(x).multiplyScalar(M.y).addScaledVector(S,-y.y).multiplyScalar(O),_.copy(S).multiplyScalar(y.x).addScaledVector(x,-M.x).multiplyScalar(O),d[A].add(C),d[D].add(C),d[fe].add(C),p[A].add(_),p[D].add(_),p[fe].add(_))}let R=this.groups;R.length===0&&(R=[{start:0,count:e.count}]);for(let A=0,D=R.length;A<D;++A){const fe=R[A],O=fe.start,te=fe.count;for(let Q=O,oe=O+te;Q<oe;Q+=3)v(e.getX(Q+0),e.getX(Q+1),e.getX(Q+2))}const L=new ne,b=new ne,F=new ne,U=new ne;function z(A){F.fromBufferAttribute(o,A),U.copy(F);const D=d[A];L.copy(D),L.sub(F.multiplyScalar(F.dot(D))).normalize(),b.crossVectors(U,D);const O=b.dot(p[A])<0?-1:1;c.setXYZW(A,L.x,L.y,L.z,O)}for(let A=0,D=R.length;A<D;++A){const fe=R[A],O=fe.start,te=fe.count;for(let Q=O,oe=O+te;Q<oe;Q+=3)z(e.getX(Q+0)),z(e.getX(Q+1)),z(e.getX(Q+2))}}computeVertexNormals(){const e=this.index,n=this.getAttribute("position");if(n!==void 0){let r=this.getAttribute("normal");if(r===void 0)r=new gi(new Float32Array(n.count*3),3),this.setAttribute("normal",r);else for(let g=0,y=r.count;g<y;g++)r.setXYZ(g,0,0,0);const o=new ne,u=new ne,c=new ne,d=new ne,p=new ne,m=new ne,x=new ne,S=new ne;if(e)for(let g=0,y=e.count;g<y;g+=3){const M=e.getX(g+0),C=e.getX(g+1),_=e.getX(g+2);o.fromBufferAttribute(n,M),u.fromBufferAttribute(n,C),c.fromBufferAttribute(n,_),x.subVectors(c,u),S.subVectors(o,u),x.cross(S),d.fromBufferAttribute(r,M),p.fromBufferAttribute(r,C),m.fromBufferAttribute(r,_),d.add(x),p.add(x),m.add(x),r.setXYZ(M,d.x,d.y,d.z),r.setXYZ(C,p.x,p.y,p.z),r.setXYZ(_,m.x,m.y,m.z)}else for(let g=0,y=n.count;g<y;g+=3)o.fromBufferAttribute(n,g+0),u.fromBufferAttribute(n,g+1),c.fromBufferAttribute(n,g+2),x.subVectors(c,u),S.subVectors(o,u),x.cross(S),r.setXYZ(g+0,x.x,x.y,x.z),r.setXYZ(g+1,x.x,x.y,x.z),r.setXYZ(g+2,x.x,x.y,x.z);this.normalizeNormals(),r.needsUpdate=!0}}normalizeNormals(){const e=this.attributes.normal;for(let n=0,r=e.count;n<r;n++)on.fromBufferAttribute(e,n),on.normalize(),e.setXYZ(n,on.x,on.y,on.z)}toNonIndexed(){function e(d,p){const m=d.array,x=d.itemSize,S=d.normalized,g=new m.constructor(p.length*x);let y=0,M=0;for(let C=0,_=p.length;C<_;C++){d.isInterleavedBufferAttribute?y=p[C]*d.data.stride+d.offset:y=p[C]*x;for(let v=0;v<x;v++)g[M++]=m[y++]}return new gi(g,x,S)}if(this.index===null)return ot("BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const n=new Gn,r=this.index.array,o=this.attributes;for(const d in o){const p=o[d],m=e(p,r);n.setAttribute(d,m)}const u=this.morphAttributes;for(const d in u){const p=[],m=u[d];for(let x=0,S=m.length;x<S;x++){const g=m[x],y=e(g,r);p.push(y)}n.morphAttributes[d]=p}n.morphTargetsRelative=this.morphTargetsRelative;const c=this.groups;for(let d=0,p=c.length;d<p;d++){const m=c[d];n.addGroup(m.start,m.count,m.materialIndex)}return n}toJSON(){const e={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.type,this.name!==""&&(e.name=this.name),Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0){const p=this.parameters;for(const m in p)p[m]!==void 0&&(e[m]=p[m]);return e}e.data={attributes:{}};const n=this.index;n!==null&&(e.data.index={type:n.array.constructor.name,array:Array.prototype.slice.call(n.array)});const r=this.attributes;for(const p in r){const m=r[p];e.data.attributes[p]=m.toJSON(e.data)}const o={};let u=!1;for(const p in this.morphAttributes){const m=this.morphAttributes[p],x=[];for(let S=0,g=m.length;S<g;S++){const y=m[S];x.push(y.toJSON(e.data))}x.length>0&&(o[p]=x,u=!0)}u&&(e.data.morphAttributes=o,e.data.morphTargetsRelative=this.morphTargetsRelative);const c=this.groups;c.length>0&&(e.data.groups=JSON.parse(JSON.stringify(c)));const d=this.boundingSphere;return d!==null&&(e.data.boundingSphere=d.toJSON()),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const n={};this.name=e.name;const r=e.index;r!==null&&this.setIndex(r.clone());const o=e.attributes;for(const m in o){const x=o[m];this.setAttribute(m,x.clone(n))}const u=e.morphAttributes;for(const m in u){const x=[],S=u[m];for(let g=0,y=S.length;g<y;g++)x.push(S[g].clone(n));this.morphAttributes[m]=x}this.morphTargetsRelative=e.morphTargetsRelative;const c=e.groups;for(let m=0,x=c.length;m<x;m++){const S=c[m];this.addGroup(S.start,S.count,S.materialIndex)}const d=e.boundingBox;d!==null&&(this.boundingBox=d.clone());const p=e.boundingSphere;return p!==null&&(this.boundingSphere=p.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}let lv=0;class Xa extends Ys{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:lv++}),this.uuid=Ga(),this.name="",this.type="Material",this.blending=zs,this.side=Rr,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=af,this.blendDst=of,this.blendEquation=Zr,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new bt(0,0,0),this.blendAlpha=0,this.depthFunc=Hs,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Hp,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=As,this.stencilZFail=As,this.stencilZPass=As,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(const n in e){const r=e[n];if(r===void 0){ot(`Material: parameter '${n}' has value of undefined.`);continue}const o=this[n];if(o===void 0){ot(`Material: '${n}' is not a property of THREE.${this.type}.`);continue}o&&o.isColor?o.set(r):o&&o.isVector3&&r&&r.isVector3?o.copy(r):this[n]=r}}toJSON(e){const n=e===void 0||typeof e=="string";n&&(e={textures:{},images:{}});const r={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};r.uuid=this.uuid,r.type=this.type,this.name!==""&&(r.name=this.name),this.color&&this.color.isColor&&(r.color=this.color.getHex()),this.roughness!==void 0&&(r.roughness=this.roughness),this.metalness!==void 0&&(r.metalness=this.metalness),this.sheen!==void 0&&(r.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(r.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(r.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(r.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(r.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(r.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(r.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(r.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(r.shininess=this.shininess),this.clearcoat!==void 0&&(r.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(r.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(r.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(r.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(r.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,r.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(r.sheenColorMap=this.sheenColorMap.toJSON(e).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(r.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(e).uuid),this.dispersion!==void 0&&(r.dispersion=this.dispersion),this.iridescence!==void 0&&(r.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(r.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(r.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(r.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(r.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(r.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(r.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(r.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(r.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(r.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(r.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(r.lightMap=this.lightMap.toJSON(e).uuid,r.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(r.aoMap=this.aoMap.toJSON(e).uuid,r.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(r.bumpMap=this.bumpMap.toJSON(e).uuid,r.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(r.normalMap=this.normalMap.toJSON(e).uuid,r.normalMapType=this.normalMapType,r.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(r.displacementMap=this.displacementMap.toJSON(e).uuid,r.displacementScale=this.displacementScale,r.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(r.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(r.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(r.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(r.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(r.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(r.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(r.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(r.combine=this.combine)),this.envMapRotation!==void 0&&(r.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(r.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(r.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(r.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(r.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(r.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(r.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(r.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(r.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(r.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(r.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(r.size=this.size),this.shadowSide!==null&&(r.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(r.sizeAttenuation=this.sizeAttenuation),this.blending!==zs&&(r.blending=this.blending),this.side!==Rr&&(r.side=this.side),this.vertexColors===!0&&(r.vertexColors=!0),this.opacity<1&&(r.opacity=this.opacity),this.transparent===!0&&(r.transparent=!0),this.blendSrc!==af&&(r.blendSrc=this.blendSrc),this.blendDst!==of&&(r.blendDst=this.blendDst),this.blendEquation!==Zr&&(r.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(r.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(r.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(r.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(r.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(r.blendAlpha=this.blendAlpha),this.depthFunc!==Hs&&(r.depthFunc=this.depthFunc),this.depthTest===!1&&(r.depthTest=this.depthTest),this.depthWrite===!1&&(r.depthWrite=this.depthWrite),this.colorWrite===!1&&(r.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(r.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==Hp&&(r.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(r.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(r.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==As&&(r.stencilFail=this.stencilFail),this.stencilZFail!==As&&(r.stencilZFail=this.stencilZFail),this.stencilZPass!==As&&(r.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(r.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(r.rotation=this.rotation),this.polygonOffset===!0&&(r.polygonOffset=!0),this.polygonOffsetFactor!==0&&(r.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(r.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(r.linewidth=this.linewidth),this.dashSize!==void 0&&(r.dashSize=this.dashSize),this.gapSize!==void 0&&(r.gapSize=this.gapSize),this.scale!==void 0&&(r.scale=this.scale),this.dithering===!0&&(r.dithering=!0),this.alphaTest>0&&(r.alphaTest=this.alphaTest),this.alphaHash===!0&&(r.alphaHash=!0),this.alphaToCoverage===!0&&(r.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(r.premultipliedAlpha=!0),this.forceSinglePass===!0&&(r.forceSinglePass=!0),this.allowOverride===!1&&(r.allowOverride=!1),this.wireframe===!0&&(r.wireframe=!0),this.wireframeLinewidth>1&&(r.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(r.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(r.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(r.flatShading=!0),this.visible===!1&&(r.visible=!1),this.toneMapped===!1&&(r.toneMapped=!1),this.fog===!1&&(r.fog=!1),Object.keys(this.userData).length>0&&(r.userData=this.userData);function o(u){const c=[];for(const d in u){const p=u[d];delete p.metadata,c.push(p)}return c}if(n){const u=o(e.textures),c=o(e.images);u.length>0&&(r.textures=u),c.length>0&&(r.images=c)}return r}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;const n=e.clippingPlanes;let r=null;if(n!==null){const o=n.length;r=new Array(o);for(let u=0;u!==o;++u)r[u]=n[u].clone()}return this.clippingPlanes=r,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.allowOverride=e.allowOverride,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}}const ji=new ne,qc=new ne,fl=new ne,Tr=new ne,$c=new ne,dl=new ne,Kc=new ne;class rg{constructor(e=new ne,n=new ne(0,0,-1)){this.origin=e,this.direction=n}set(e,n){return this.origin.copy(e),this.direction.copy(n),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,n){return n.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,ji)),this}closestPointToPoint(e,n){n.subVectors(e,this.origin);const r=n.dot(this.direction);return r<0?n.copy(this.origin):n.copy(this.origin).addScaledVector(this.direction,r)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){const n=ji.subVectors(e,this.origin).dot(this.direction);return n<0?this.origin.distanceToSquared(e):(ji.copy(this.origin).addScaledVector(this.direction,n),ji.distanceToSquared(e))}distanceSqToSegment(e,n,r,o){qc.copy(e).add(n).multiplyScalar(.5),fl.copy(n).sub(e).normalize(),Tr.copy(this.origin).sub(qc);const u=e.distanceTo(n)*.5,c=-this.direction.dot(fl),d=Tr.dot(this.direction),p=-Tr.dot(fl),m=Tr.lengthSq(),x=Math.abs(1-c*c);let S,g,y,M;if(x>0)if(S=c*p-d,g=c*d-p,M=u*x,S>=0)if(g>=-M)if(g<=M){const C=1/x;S*=C,g*=C,y=S*(S+c*g+2*d)+g*(c*S+g+2*p)+m}else g=u,S=Math.max(0,-(c*g+d)),y=-S*S+g*(g+2*p)+m;else g=-u,S=Math.max(0,-(c*g+d)),y=-S*S+g*(g+2*p)+m;else g<=-M?(S=Math.max(0,-(-c*u+d)),g=S>0?-u:Math.min(Math.max(-u,-p),u),y=-S*S+g*(g+2*p)+m):g<=M?(S=0,g=Math.min(Math.max(-u,-p),u),y=g*(g+2*p)+m):(S=Math.max(0,-(c*u+d)),g=S>0?u:Math.min(Math.max(-u,-p),u),y=-S*S+g*(g+2*p)+m);else g=c>0?-u:u,S=Math.max(0,-(c*g+d)),y=-S*S+g*(g+2*p)+m;return r&&r.copy(this.origin).addScaledVector(this.direction,S),o&&o.copy(qc).addScaledVector(fl,g),y}intersectSphere(e,n){ji.subVectors(e.center,this.origin);const r=ji.dot(this.direction),o=ji.dot(ji)-r*r,u=e.radius*e.radius;if(o>u)return null;const c=Math.sqrt(u-o),d=r-c,p=r+c;return p<0?null:d<0?this.at(p,n):this.at(d,n)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){const n=e.normal.dot(this.direction);if(n===0)return e.distanceToPoint(this.origin)===0?0:null;const r=-(this.origin.dot(e.normal)+e.constant)/n;return r>=0?r:null}intersectPlane(e,n){const r=this.distanceToPlane(e);return r===null?null:this.at(r,n)}intersectsPlane(e){const n=e.distanceToPoint(this.origin);return n===0||e.normal.dot(this.direction)*n<0}intersectBox(e,n){let r,o,u,c,d,p;const m=1/this.direction.x,x=1/this.direction.y,S=1/this.direction.z,g=this.origin;return m>=0?(r=(e.min.x-g.x)*m,o=(e.max.x-g.x)*m):(r=(e.max.x-g.x)*m,o=(e.min.x-g.x)*m),x>=0?(u=(e.min.y-g.y)*x,c=(e.max.y-g.y)*x):(u=(e.max.y-g.y)*x,c=(e.min.y-g.y)*x),r>c||u>o||((u>r||isNaN(r))&&(r=u),(c<o||isNaN(o))&&(o=c),S>=0?(d=(e.min.z-g.z)*S,p=(e.max.z-g.z)*S):(d=(e.max.z-g.z)*S,p=(e.min.z-g.z)*S),r>p||d>o)||((d>r||r!==r)&&(r=d),(p<o||o!==o)&&(o=p),o<0)?null:this.at(r>=0?r:o,n)}intersectsBox(e){return this.intersectBox(e,ji)!==null}intersectTriangle(e,n,r,o,u){$c.subVectors(n,e),dl.subVectors(r,e),Kc.crossVectors($c,dl);let c=this.direction.dot(Kc),d;if(c>0){if(o)return null;d=1}else if(c<0)d=-1,c=-c;else return null;Tr.subVectors(this.origin,e);const p=d*this.direction.dot(dl.crossVectors(Tr,dl));if(p<0)return null;const m=d*this.direction.dot($c.cross(Tr));if(m<0||p+m>c)return null;const x=-d*Tr.dot(Kc);return x<0?null:this.at(x/c,u)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class ka extends Xa{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new bt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Qi,this.combine=Fm,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}}const rm=new $t,jr=new rg,hl=new kl,sm=new ne,pl=new ne,ml=new ne,gl=new ne,Zc=new ne,_l=new ne,am=new ne,vl=new ne;class ii extends Un{constructor(e=new Gn,n=new ka){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=n,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,n){return super.copy(e,n),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){const n=this.geometry.morphAttributes,r=Object.keys(n);if(r.length>0){const o=n[r[0]];if(o!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let u=0,c=o.length;u<c;u++){const d=o[u].name||String(u);this.morphTargetInfluences.push(0),this.morphTargetDictionary[d]=u}}}}getVertexPosition(e,n){const r=this.geometry,o=r.attributes.position,u=r.morphAttributes.position,c=r.morphTargetsRelative;n.fromBufferAttribute(o,e);const d=this.morphTargetInfluences;if(u&&d){_l.set(0,0,0);for(let p=0,m=u.length;p<m;p++){const x=d[p],S=u[p];x!==0&&(Zc.fromBufferAttribute(S,e),c?_l.addScaledVector(Zc,x):_l.addScaledVector(Zc.sub(n),x))}n.add(_l)}return n}raycast(e,n){const r=this.geometry,o=this.material,u=this.matrixWorld;o!==void 0&&(r.boundingSphere===null&&r.computeBoundingSphere(),hl.copy(r.boundingSphere),hl.applyMatrix4(u),jr.copy(e.ray).recast(e.near),!(hl.containsPoint(jr.origin)===!1&&(jr.intersectSphere(hl,sm)===null||jr.origin.distanceToSquared(sm)>(e.far-e.near)**2))&&(rm.copy(u).invert(),jr.copy(e.ray).applyMatrix4(rm),!(r.boundingBox!==null&&jr.intersectsBox(r.boundingBox)===!1)&&this._computeIntersections(e,n,jr)))}_computeIntersections(e,n,r){let o;const u=this.geometry,c=this.material,d=u.index,p=u.attributes.position,m=u.attributes.uv,x=u.attributes.uv1,S=u.attributes.normal,g=u.groups,y=u.drawRange;if(d!==null)if(Array.isArray(c))for(let M=0,C=g.length;M<C;M++){const _=g[M],v=c[_.materialIndex],R=Math.max(_.start,y.start),L=Math.min(d.count,Math.min(_.start+_.count,y.start+y.count));for(let b=R,F=L;b<F;b+=3){const U=d.getX(b),z=d.getX(b+1),A=d.getX(b+2);o=xl(this,v,e,r,m,x,S,U,z,A),o&&(o.faceIndex=Math.floor(b/3),o.face.materialIndex=_.materialIndex,n.push(o))}}else{const M=Math.max(0,y.start),C=Math.min(d.count,y.start+y.count);for(let _=M,v=C;_<v;_+=3){const R=d.getX(_),L=d.getX(_+1),b=d.getX(_+2);o=xl(this,c,e,r,m,x,S,R,L,b),o&&(o.faceIndex=Math.floor(_/3),n.push(o))}}else if(p!==void 0)if(Array.isArray(c))for(let M=0,C=g.length;M<C;M++){const _=g[M],v=c[_.materialIndex],R=Math.max(_.start,y.start),L=Math.min(p.count,Math.min(_.start+_.count,y.start+y.count));for(let b=R,F=L;b<F;b+=3){const U=b,z=b+1,A=b+2;o=xl(this,v,e,r,m,x,S,U,z,A),o&&(o.faceIndex=Math.floor(b/3),o.face.materialIndex=_.materialIndex,n.push(o))}}else{const M=Math.max(0,y.start),C=Math.min(p.count,y.start+y.count);for(let _=M,v=C;_<v;_+=3){const R=_,L=_+1,b=_+2;o=xl(this,c,e,r,m,x,S,R,L,b),o&&(o.faceIndex=Math.floor(_/3),n.push(o))}}}}function uv(s,e,n,r,o,u,c,d){let p;if(e.side===In?p=r.intersectTriangle(c,u,o,!0,d):p=r.intersectTriangle(o,u,c,e.side===Rr,d),p===null)return null;vl.copy(d),vl.applyMatrix4(s.matrixWorld);const m=n.ray.origin.distanceTo(vl);return m<n.near||m>n.far?null:{distance:m,point:vl.clone(),object:s}}function xl(s,e,n,r,o,u,c,d,p,m){s.getVertexPosition(d,pl),s.getVertexPosition(p,ml),s.getVertexPosition(m,gl);const x=uv(s,e,n,r,pl,ml,gl,am);if(x){const S=new ne;pi.getBarycoord(am,pl,ml,gl,S),o&&(x.uv=pi.getInterpolatedAttribute(o,d,p,m,S,new Lt)),u&&(x.uv1=pi.getInterpolatedAttribute(u,d,p,m,S,new Lt)),c&&(x.normal=pi.getInterpolatedAttribute(c,d,p,m,S,new ne),x.normal.dot(r.direction)>0&&x.normal.multiplyScalar(-1));const g={a:d,b:p,c:m,normal:new ne,materialIndex:0};pi.getNormal(pl,ml,gl,g.normal),x.face=g,x.barycoord=S}return x}class cv extends En{constructor(e=null,n=1,r=1,o,u,c,d,p,m=cn,x=cn,S,g){super(null,c,d,p,m,x,o,u,S,g),this.isDataTexture=!0,this.image={data:e,width:n,height:r},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}const Qc=new ne,fv=new ne,dv=new ft;class Kr{constructor(e=new ne(1,0,0),n=0){this.isPlane=!0,this.normal=e,this.constant=n}set(e,n){return this.normal.copy(e),this.constant=n,this}setComponents(e,n,r,o){return this.normal.set(e,n,r),this.constant=o,this}setFromNormalAndCoplanarPoint(e,n){return this.normal.copy(e),this.constant=-n.dot(this.normal),this}setFromCoplanarPoints(e,n,r){const o=Qc.subVectors(r,n).cross(fv.subVectors(e,n)).normalize();return this.setFromNormalAndCoplanarPoint(o,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){const e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,n){return n.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,n){const r=e.delta(Qc),o=this.normal.dot(r);if(o===0)return this.distanceToPoint(e.start)===0?n.copy(e.start):null;const u=-(e.start.dot(this.normal)+this.constant)/o;return u<0||u>1?null:n.copy(e.start).addScaledVector(r,u)}intersectsLine(e){const n=this.distanceToPoint(e.start),r=this.distanceToPoint(e.end);return n<0&&r>0||r<0&&n>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,n){const r=n||dv.getNormalMatrix(e),o=this.coplanarPoint(Qc).applyMatrix4(e),u=this.normal.applyMatrix3(r).normalize();return this.constant=-o.dot(u),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}}const Yr=new kl,hv=new Lt(.5,.5),Sl=new ne;class sg{constructor(e=new Kr,n=new Kr,r=new Kr,o=new Kr,u=new Kr,c=new Kr){this.planes=[e,n,r,o,u,c]}set(e,n,r,o,u,c){const d=this.planes;return d[0].copy(e),d[1].copy(n),d[2].copy(r),d[3].copy(o),d[4].copy(u),d[5].copy(c),this}copy(e){const n=this.planes;for(let r=0;r<6;r++)n[r].copy(e.planes[r]);return this}setFromProjectionMatrix(e,n=Ci,r=!1){const o=this.planes,u=e.elements,c=u[0],d=u[1],p=u[2],m=u[3],x=u[4],S=u[5],g=u[6],y=u[7],M=u[8],C=u[9],_=u[10],v=u[11],R=u[12],L=u[13],b=u[14],F=u[15];if(o[0].setComponents(m-c,y-x,v-M,F-R).normalize(),o[1].setComponents(m+c,y+x,v+M,F+R).normalize(),o[2].setComponents(m+d,y+S,v+C,F+L).normalize(),o[3].setComponents(m-d,y-S,v-C,F-L).normalize(),r)o[4].setComponents(p,g,_,b).normalize(),o[5].setComponents(m-p,y-g,v-_,F-b).normalize();else if(o[4].setComponents(m-p,y-g,v-_,F-b).normalize(),n===Ci)o[5].setComponents(m+p,y+g,v+_,F+b).normalize();else if(n===Il)o[5].setComponents(p,g,_,b).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+n);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),Yr.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{const n=e.geometry;n.boundingSphere===null&&n.computeBoundingSphere(),Yr.copy(n.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(Yr)}intersectsSprite(e){Yr.center.set(0,0,0);const n=hv.distanceTo(e.center);return Yr.radius=.7071067811865476+n,Yr.applyMatrix4(e.matrixWorld),this.intersectsSphere(Yr)}intersectsSphere(e){const n=this.planes,r=e.center,o=-e.radius;for(let u=0;u<6;u++)if(n[u].distanceToPoint(r)<o)return!1;return!0}intersectsBox(e){const n=this.planes;for(let r=0;r<6;r++){const o=n[r];if(Sl.x=o.normal.x>0?e.max.x:e.min.x,Sl.y=o.normal.y>0?e.max.y:e.min.y,Sl.z=o.normal.z>0?e.max.z:e.min.z,o.distanceToPoint(Sl)<0)return!1}return!0}containsPoint(e){const n=this.planes;for(let r=0;r<6;r++)if(n[r].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}class ag extends Xa{constructor(e){super(),this.isPointsMaterial=!0,this.type="PointsMaterial",this.color=new bt(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.alphaMap=e.alphaMap,this.size=e.size,this.sizeAttenuation=e.sizeAttenuation,this.fog=e.fog,this}}const om=new $t,Kf=new rg,yl=new kl,Ml=new ne;class pv extends Un{constructor(e=new Gn,n=new ag){super(),this.isPoints=!0,this.type="Points",this.geometry=e,this.material=n,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(e,n){return super.copy(e,n),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}raycast(e,n){const r=this.geometry,o=this.matrixWorld,u=e.params.Points.threshold,c=r.drawRange;if(r.boundingSphere===null&&r.computeBoundingSphere(),yl.copy(r.boundingSphere),yl.applyMatrix4(o),yl.radius+=u,e.ray.intersectsSphere(yl)===!1)return;om.copy(o).invert(),Kf.copy(e.ray).applyMatrix4(om);const d=u/((this.scale.x+this.scale.y+this.scale.z)/3),p=d*d,m=r.index,S=r.attributes.position;if(m!==null){const g=Math.max(0,c.start),y=Math.min(m.count,c.start+c.count);for(let M=g,C=y;M<C;M++){const _=m.getX(M);Ml.fromBufferAttribute(S,_),lm(Ml,_,p,o,e,n,this)}}else{const g=Math.max(0,c.start),y=Math.min(S.count,c.start+c.count);for(let M=g,C=y;M<C;M++)Ml.fromBufferAttribute(S,M),lm(Ml,M,p,o,e,n,this)}}updateMorphTargets(){const n=this.geometry.morphAttributes,r=Object.keys(n);if(r.length>0){const o=n[r[0]];if(o!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let u=0,c=o.length;u<c;u++){const d=o[u].name||String(u);this.morphTargetInfluences.push(0),this.morphTargetDictionary[d]=u}}}}}function lm(s,e,n,r,o,u,c){const d=Kf.distanceSqToPoint(s);if(d<n){const p=new ne;Kf.closestPointToPoint(s,p),p.applyMatrix4(r);const m=o.ray.origin.distanceTo(p);if(m<o.near||m>o.far)return;u.push({distance:m,distanceToRay:Math.sqrt(d),point:p,index:e,face:null,faceIndex:null,barycoord:null,object:c})}}class og extends En{constructor(e=[],n=ts,r,o,u,c,d,p,m,x){super(e,n,r,o,u,c,d,p,m,x),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}}class Ha extends En{constructor(e,n,r=Pi,o,u,c,d=cn,p=cn,m,x=Zi,S=1){if(x!==Zi&&x!==es)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");const g={width:e,height:n,depth:S};super(g,o,u,c,d,p,x,r,m),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new ud(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){const n=super.toJSON(e);return this.compareFunction!==null&&(n.compareFunction=this.compareFunction),n}}class mv extends Ha{constructor(e,n=Pi,r=ts,o,u,c=cn,d=cn,p,m=Zi){const x={width:e,height:e,depth:1},S=[x,x,x,x,x,x];super(e,e,n,r,o,u,c,d,p,m),this.image=S,this.isCubeDepthTexture=!0,this.isCubeTexture=!0}get images(){return this.image}set images(e){this.image=e}}class lg extends En{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}copy(e){return super.copy(e),this.sourceTexture=e.sourceTexture,this}}class ja extends Gn{constructor(e=1,n=1,r=1,o=1,u=1,c=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:n,depth:r,widthSegments:o,heightSegments:u,depthSegments:c};const d=this;o=Math.floor(o),u=Math.floor(u),c=Math.floor(c);const p=[],m=[],x=[],S=[];let g=0,y=0;M("z","y","x",-1,-1,r,n,e,c,u,0),M("z","y","x",1,-1,r,n,-e,c,u,1),M("x","z","y",1,1,e,r,n,o,c,2),M("x","z","y",1,-1,e,r,-n,o,c,3),M("x","y","z",1,-1,e,n,r,o,u,4),M("x","y","z",-1,-1,e,n,-r,o,u,5),this.setIndex(p),this.setAttribute("position",new Tn(m,3)),this.setAttribute("normal",new Tn(x,3)),this.setAttribute("uv",new Tn(S,2));function M(C,_,v,R,L,b,F,U,z,A,D){const fe=b/z,O=F/A,te=b/2,Q=F/2,oe=U/2,K=z+1,ee=A+1;let W=0,q=0;const ae=new ne;for(let le=0;le<ee;le++){const I=le*O-Q;for(let j=0;j<K;j++){const Ce=j*fe-te;ae[C]=Ce*R,ae[_]=I*L,ae[v]=oe,m.push(ae.x,ae.y,ae.z),ae[C]=0,ae[_]=0,ae[v]=U>0?1:-1,x.push(ae.x,ae.y,ae.z),S.push(j/z),S.push(1-le/A),W+=1}}for(let le=0;le<A;le++)for(let I=0;I<z;I++){const j=g+I+K*le,Ce=g+I+K*(le+1),Xe=g+(I+1)+K*(le+1),Ze=g+(I+1)+K*le;p.push(j,Ce,Ze),p.push(Ce,Xe,Ze),q+=6}d.addGroup(y,q,D),y+=q,g+=W}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new ja(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}}class zl extends Gn{constructor(e=1,n=1,r=1,o=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:n,widthSegments:r,heightSegments:o};const u=e/2,c=n/2,d=Math.floor(r),p=Math.floor(o),m=d+1,x=p+1,S=e/d,g=n/p,y=[],M=[],C=[],_=[];for(let v=0;v<x;v++){const R=v*g-c;for(let L=0;L<m;L++){const b=L*S-u;M.push(b,-R,0),C.push(0,0,1),_.push(L/d),_.push(1-v/p)}}for(let v=0;v<p;v++)for(let R=0;R<d;R++){const L=R+m*v,b=R+m*(v+1),F=R+1+m*(v+1),U=R+1+m*v;y.push(L,b,U),y.push(b,F,U)}this.setIndex(y),this.setAttribute("position",new Tn(M,3)),this.setAttribute("normal",new Tn(C,3)),this.setAttribute("uv",new Tn(_,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new zl(e.width,e.height,e.widthSegments,e.heightSegments)}}class cd extends Gn{constructor(e=.5,n=1,r=32,o=1,u=0,c=Math.PI*2){super(),this.type="RingGeometry",this.parameters={innerRadius:e,outerRadius:n,thetaSegments:r,phiSegments:o,thetaStart:u,thetaLength:c},r=Math.max(3,r),o=Math.max(1,o);const d=[],p=[],m=[],x=[];let S=e;const g=(n-e)/o,y=new ne,M=new Lt;for(let C=0;C<=o;C++){for(let _=0;_<=r;_++){const v=u+_/r*c;y.x=S*Math.cos(v),y.y=S*Math.sin(v),p.push(y.x,y.y,y.z),m.push(0,0,1),M.x=(y.x/n+1)/2,M.y=(y.y/n+1)/2,x.push(M.x,M.y)}S+=g}for(let C=0;C<o;C++){const _=C*(r+1);for(let v=0;v<r;v++){const R=v+_,L=R,b=R+r+1,F=R+r+2,U=R+1;d.push(L,b,U),d.push(b,F,U)}}this.setIndex(d),this.setAttribute("position",new Tn(p,3)),this.setAttribute("normal",new Tn(m,3)),this.setAttribute("uv",new Tn(x,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new cd(e.innerRadius,e.outerRadius,e.thetaSegments,e.phiSegments,e.thetaStart,e.thetaLength)}}class Ol extends Gn{constructor(e=1,n=32,r=16,o=0,u=Math.PI*2,c=0,d=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:e,widthSegments:n,heightSegments:r,phiStart:o,phiLength:u,thetaStart:c,thetaLength:d},n=Math.max(3,Math.floor(n)),r=Math.max(2,Math.floor(r));const p=Math.min(c+d,Math.PI);let m=0;const x=[],S=new ne,g=new ne,y=[],M=[],C=[],_=[];for(let v=0;v<=r;v++){const R=[],L=v/r;let b=0;v===0&&c===0?b=.5/n:v===r&&p===Math.PI&&(b=-.5/n);for(let F=0;F<=n;F++){const U=F/n;S.x=-e*Math.cos(o+U*u)*Math.sin(c+L*d),S.y=e*Math.cos(c+L*d),S.z=e*Math.sin(o+U*u)*Math.sin(c+L*d),M.push(S.x,S.y,S.z),g.copy(S).normalize(),C.push(g.x,g.y,g.z),_.push(U+b,1-L),R.push(m++)}x.push(R)}for(let v=0;v<r;v++)for(let R=0;R<n;R++){const L=x[v][R+1],b=x[v][R],F=x[v+1][R],U=x[v+1][R+1];(v!==0||c>0)&&y.push(L,b,U),(v!==r-1||p<Math.PI)&&y.push(b,F,U)}this.setIndex(y),this.setAttribute("position",new Tn(M,3)),this.setAttribute("normal",new Tn(C,3)),this.setAttribute("uv",new Tn(_,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new Ol(e.radius,e.widthSegments,e.heightSegments,e.phiStart,e.phiLength,e.thetaStart,e.thetaLength)}}function js(s){const e={};for(const n in s){e[n]={};for(const r in s[n]){const o=s[n][r];o&&(o.isColor||o.isMatrix3||o.isMatrix4||o.isVector2||o.isVector3||o.isVector4||o.isTexture||o.isQuaternion)?o.isRenderTargetTexture?(ot("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[n][r]=null):e[n][r]=o.clone():Array.isArray(o)?e[n][r]=o.slice():e[n][r]=o}}return e}function Mn(s){const e={};for(let n=0;n<s.length;n++){const r=js(s[n]);for(const o in r)e[o]=r[o]}return e}function gv(s){const e=[];for(let n=0;n<s.length;n++)e.push(s[n].clone());return e}function ug(s){const e=s.getRenderTarget();return e===null?s.outputColorSpace:e.isXRRenderTarget===!0?e.texture.colorSpace:Et.workingColorSpace}const _v={clone:js,merge:Mn};var vv=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,xv=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class Di extends Xa{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=vv,this.fragmentShader=xv,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=js(e.uniforms),this.uniformsGroups=gv(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this.defaultAttributeValues=Object.assign({},e.defaultAttributeValues),this.index0AttributeName=e.index0AttributeName,this.uniformsNeedUpdate=e.uniformsNeedUpdate,this}toJSON(e){const n=super.toJSON(e);n.glslVersion=this.glslVersion,n.uniforms={};for(const o in this.uniforms){const c=this.uniforms[o].value;c&&c.isTexture?n.uniforms[o]={type:"t",value:c.toJSON(e).uuid}:c&&c.isColor?n.uniforms[o]={type:"c",value:c.getHex()}:c&&c.isVector2?n.uniforms[o]={type:"v2",value:c.toArray()}:c&&c.isVector3?n.uniforms[o]={type:"v3",value:c.toArray()}:c&&c.isVector4?n.uniforms[o]={type:"v4",value:c.toArray()}:c&&c.isMatrix3?n.uniforms[o]={type:"m3",value:c.toArray()}:c&&c.isMatrix4?n.uniforms[o]={type:"m4",value:c.toArray()}:n.uniforms[o]={value:c}}Object.keys(this.defines).length>0&&(n.defines=this.defines),n.vertexShader=this.vertexShader,n.fragmentShader=this.fragmentShader,n.lights=this.lights,n.clipping=this.clipping;const r={};for(const o in this.extensions)this.extensions[o]===!0&&(r[o]=!0);return Object.keys(r).length>0&&(n.extensions=r),n}}class Sv extends Di{constructor(e){super(e),this.isRawShaderMaterial=!0,this.type="RawShaderMaterial"}}class yv extends Xa{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=D0,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}}class Mv extends Xa{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}}const El=new ne,Tl=new qs,Mi=new ne;class cg extends Un{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new $t,this.projectionMatrix=new $t,this.projectionMatrixInverse=new $t,this.coordinateSystem=Ci,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,n){return super.copy(e,n),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorld.decompose(El,Tl,Mi),Mi.x===1&&Mi.y===1&&Mi.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(El,Tl,Mi.set(1,1,1)).invert()}updateWorldMatrix(e,n){super.updateWorldMatrix(e,n),this.matrixWorld.decompose(El,Tl,Mi),Mi.x===1&&Mi.y===1&&Mi.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(El,Tl,Mi.set(1,1,1)).invert()}clone(){return new this.constructor().copy(this)}}const wr=new ne,um=new Lt,cm=new Lt;class ti extends cg{constructor(e=50,n=1,r=.1,o=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=r,this.far=o,this.focus=10,this.aspect=n,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,n){return super.copy(e,n),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){const n=.5*this.getFilmHeight()/e;this.fov=$f*2*Math.atan(n),this.updateProjectionMatrix()}getFocalLength(){const e=Math.tan(bc*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return $f*2*Math.atan(Math.tan(bc*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,n,r){wr.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(wr.x,wr.y).multiplyScalar(-e/wr.z),wr.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),r.set(wr.x,wr.y).multiplyScalar(-e/wr.z)}getViewSize(e,n){return this.getViewBounds(e,um,cm),n.subVectors(cm,um)}setViewOffset(e,n,r,o,u,c){this.aspect=e/n,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=n,this.view.offsetX=r,this.view.offsetY=o,this.view.width=u,this.view.height=c,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=this.near;let n=e*Math.tan(bc*.5*this.fov)/this.zoom,r=2*n,o=this.aspect*r,u=-.5*o;const c=this.view;if(this.view!==null&&this.view.enabled){const p=c.fullWidth,m=c.fullHeight;u+=c.offsetX*o/p,n-=c.offsetY*r/m,o*=c.width/p,r*=c.height/m}const d=this.filmOffset;d!==0&&(u+=e*d/this.getFilmWidth()),this.projectionMatrix.makePerspective(u,u+o,n,n-r,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const n=super.toJSON(e);return n.object.fov=this.fov,n.object.zoom=this.zoom,n.object.near=this.near,n.object.far=this.far,n.object.focus=this.focus,n.object.aspect=this.aspect,this.view!==null&&(n.object.view=Object.assign({},this.view)),n.object.filmGauge=this.filmGauge,n.object.filmOffset=this.filmOffset,n}}class fg extends cg{constructor(e=-1,n=1,r=1,o=-1,u=.1,c=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=n,this.top=r,this.bottom=o,this.near=u,this.far=c,this.updateProjectionMatrix()}copy(e,n){return super.copy(e,n),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,n,r,o,u,c){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=n,this.view.offsetX=r,this.view.offsetY=o,this.view.width=u,this.view.height=c,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const e=(this.right-this.left)/(2*this.zoom),n=(this.top-this.bottom)/(2*this.zoom),r=(this.right+this.left)/2,o=(this.top+this.bottom)/2;let u=r-e,c=r+e,d=o+n,p=o-n;if(this.view!==null&&this.view.enabled){const m=(this.right-this.left)/this.view.fullWidth/this.zoom,x=(this.top-this.bottom)/this.view.fullHeight/this.zoom;u+=m*this.view.offsetX,c=u+m*this.view.width,d-=x*this.view.offsetY,p=d-x*this.view.height}this.projectionMatrix.makeOrthographic(u,c,d,p,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){const n=super.toJSON(e);return n.object.zoom=this.zoom,n.object.left=this.left,n.object.right=this.right,n.object.top=this.top,n.object.bottom=this.bottom,n.object.near=this.near,n.object.far=this.far,this.view!==null&&(n.object.view=Object.assign({},this.view)),n}}const Os=-90,Bs=1;class Ev extends Un{constructor(e,n,r){super(),this.type="CubeCamera",this.renderTarget=r,this.coordinateSystem=null,this.activeMipmapLevel=0;const o=new ti(Os,Bs,e,n);o.layers=this.layers,this.add(o);const u=new ti(Os,Bs,e,n);u.layers=this.layers,this.add(u);const c=new ti(Os,Bs,e,n);c.layers=this.layers,this.add(c);const d=new ti(Os,Bs,e,n);d.layers=this.layers,this.add(d);const p=new ti(Os,Bs,e,n);p.layers=this.layers,this.add(p);const m=new ti(Os,Bs,e,n);m.layers=this.layers,this.add(m)}updateCoordinateSystem(){const e=this.coordinateSystem,n=this.children.concat(),[r,o,u,c,d,p]=n;for(const m of n)this.remove(m);if(e===Ci)r.up.set(0,1,0),r.lookAt(1,0,0),o.up.set(0,1,0),o.lookAt(-1,0,0),u.up.set(0,0,-1),u.lookAt(0,1,0),c.up.set(0,0,1),c.lookAt(0,-1,0),d.up.set(0,1,0),d.lookAt(0,0,1),p.up.set(0,1,0),p.lookAt(0,0,-1);else if(e===Il)r.up.set(0,-1,0),r.lookAt(-1,0,0),o.up.set(0,-1,0),o.lookAt(1,0,0),u.up.set(0,0,1),u.lookAt(0,1,0),c.up.set(0,0,-1),c.lookAt(0,-1,0),d.up.set(0,-1,0),d.lookAt(0,0,1),p.up.set(0,-1,0),p.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(const m of n)this.add(m),m.updateMatrixWorld()}update(e,n){this.parent===null&&this.updateMatrixWorld();const{renderTarget:r,activeMipmapLevel:o}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());const[u,c,d,p,m,x]=this.children,S=e.getRenderTarget(),g=e.getActiveCubeFace(),y=e.getActiveMipmapLevel(),M=e.xr.enabled;e.xr.enabled=!1;const C=r.texture.generateMipmaps;r.texture.generateMipmaps=!1;let _=!1;e.isWebGLRenderer===!0?_=e.state.buffers.depth.getReversed():_=e.reversedDepthBuffer,e.setRenderTarget(r,0,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,u),e.setRenderTarget(r,1,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,c),e.setRenderTarget(r,2,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,d),e.setRenderTarget(r,3,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,p),e.setRenderTarget(r,4,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,m),r.texture.generateMipmaps=C,e.setRenderTarget(r,5,o),_&&e.autoClear===!1&&e.clearDepth(),e.render(n,x),e.setRenderTarget(S,g,y),e.xr.enabled=M,r.texture.needsPMREMUpdate=!0}}class Tv extends ti{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}}function fm(s,e,n,r){const o=wv(r);switch(n){case $m:return s*e;case Zm:return s*e/o.components*o.byteLength;case rd:return s*e/o.components*o.byteLength;case Ws:return s*e*2/o.components*o.byteLength;case sd:return s*e*2/o.components*o.byteLength;case Km:return s*e*3/o.components*o.byteLength;case mi:return s*e*4/o.components*o.byteLength;case ad:return s*e*4/o.components*o.byteLength;case Rl:case bl:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case Pl:case Dl:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case vf:case Sf:return Math.max(s,16)*Math.max(e,8)/4;case _f:case xf:return Math.max(s,8)*Math.max(e,8)/2;case yf:case Mf:case Tf:case wf:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*8;case Ef:case Af:case Cf:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case Rf:return Math.floor((s+3)/4)*Math.floor((e+3)/4)*16;case bf:return Math.floor((s+4)/5)*Math.floor((e+3)/4)*16;case Pf:return Math.floor((s+4)/5)*Math.floor((e+4)/5)*16;case Df:return Math.floor((s+5)/6)*Math.floor((e+4)/5)*16;case Lf:return Math.floor((s+5)/6)*Math.floor((e+5)/6)*16;case Nf:return Math.floor((s+7)/8)*Math.floor((e+4)/5)*16;case If:return Math.floor((s+7)/8)*Math.floor((e+5)/6)*16;case Uf:return Math.floor((s+7)/8)*Math.floor((e+7)/8)*16;case Ff:return Math.floor((s+9)/10)*Math.floor((e+4)/5)*16;case Of:return Math.floor((s+9)/10)*Math.floor((e+5)/6)*16;case Bf:return Math.floor((s+9)/10)*Math.floor((e+7)/8)*16;case kf:return Math.floor((s+9)/10)*Math.floor((e+9)/10)*16;case zf:return Math.floor((s+11)/12)*Math.floor((e+9)/10)*16;case Vf:return Math.floor((s+11)/12)*Math.floor((e+11)/12)*16;case Hf:case Gf:case Wf:return Math.ceil(s/4)*Math.ceil(e/4)*16;case Xf:case jf:return Math.ceil(s/4)*Math.ceil(e/4)*8;case Yf:case qf:return Math.ceil(s/4)*Math.ceil(e/4)*16}throw new Error(`Unable to determine texture byte length for ${n} format.`)}function wv(s){switch(s){case ni:case Xm:return{byteLength:1,components:1};case za:case jm:case Ki:return{byteLength:2,components:1};case nd:case id:return{byteLength:2,components:4};case Pi:case td:case Ai:return{byteLength:4,components:1};case Ym:case qm:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${s}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:ed}}));typeof window<"u"&&(window.__THREE__?ot("WARNING: Multiple instances of Three.js being imported."):window.__THREE__=ed);/**
 * @license
 * Copyright 2010-2026 Three.js Authors
 * SPDX-License-Identifier: MIT
 */function dg(){let s=null,e=!1,n=null,r=null;function o(u,c){n(u,c),r=s.requestAnimationFrame(o)}return{start:function(){e!==!0&&n!==null&&(r=s.requestAnimationFrame(o),e=!0)},stop:function(){s.cancelAnimationFrame(r),e=!1},setAnimationLoop:function(u){n=u},setContext:function(u){s=u}}}function Av(s){const e=new WeakMap;function n(d,p){const m=d.array,x=d.usage,S=m.byteLength,g=s.createBuffer();s.bindBuffer(p,g),s.bufferData(p,m,x),d.onUploadCallback();let y;if(m instanceof Float32Array)y=s.FLOAT;else if(typeof Float16Array<"u"&&m instanceof Float16Array)y=s.HALF_FLOAT;else if(m instanceof Uint16Array)d.isFloat16BufferAttribute?y=s.HALF_FLOAT:y=s.UNSIGNED_SHORT;else if(m instanceof Int16Array)y=s.SHORT;else if(m instanceof Uint32Array)y=s.UNSIGNED_INT;else if(m instanceof Int32Array)y=s.INT;else if(m instanceof Int8Array)y=s.BYTE;else if(m instanceof Uint8Array)y=s.UNSIGNED_BYTE;else if(m instanceof Uint8ClampedArray)y=s.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+m);return{buffer:g,type:y,bytesPerElement:m.BYTES_PER_ELEMENT,version:d.version,size:S}}function r(d,p,m){const x=p.array,S=p.updateRanges;if(s.bindBuffer(m,d),S.length===0)s.bufferSubData(m,0,x);else{S.sort((y,M)=>y.start-M.start);let g=0;for(let y=1;y<S.length;y++){const M=S[g],C=S[y];C.start<=M.start+M.count+1?M.count=Math.max(M.count,C.start+C.count-M.start):(++g,S[g]=C)}S.length=g+1;for(let y=0,M=S.length;y<M;y++){const C=S[y];s.bufferSubData(m,C.start*x.BYTES_PER_ELEMENT,x,C.start,C.count)}p.clearUpdateRanges()}p.onUploadCallback()}function o(d){return d.isInterleavedBufferAttribute&&(d=d.data),e.get(d)}function u(d){d.isInterleavedBufferAttribute&&(d=d.data);const p=e.get(d);p&&(s.deleteBuffer(p.buffer),e.delete(d))}function c(d,p){if(d.isInterleavedBufferAttribute&&(d=d.data),d.isGLBufferAttribute){const x=e.get(d);(!x||x.version<d.version)&&e.set(d,{buffer:d.buffer,type:d.type,bytesPerElement:d.elementSize,version:d.version});return}const m=e.get(d);if(m===void 0)e.set(d,n(d,p));else if(m.version<d.version){if(m.size!==d.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");r(m.buffer,d,p),m.version=d.version}}return{get:o,remove:u,update:c}}var Cv=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,Rv=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,bv=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,Pv=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Dv=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,Lv=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Nv=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,Iv=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Uv=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec4 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 );
	}
#endif`,Fv=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,Ov=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Bv=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,kv=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,zv=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,Vv=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,Hv=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,Gv=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,Wv=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,Xv=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,jv=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#endif`,Yv=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#endif`,qv=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec4 vColor;
#endif`,$v=`#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec4( 1.0 );
#endif
#ifdef USE_COLOR_ALPHA
	vColor *= color;
#elif defined( USE_COLOR )
	vColor.rgb *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.rgb *= instanceColor.rgb;
#endif
#ifdef USE_BATCHING_COLOR
	vColor *= getBatchingColor( getIndirectIndex( gl_DrawID ) );
#endif`,Kv=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,Zv=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,Qv=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,Jv=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,ex=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,tx=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,nx=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,ix="gl_FragColor = linearToOutputTexel( gl_FragColor );",rx=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,sx=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
		#ifdef ENVMAP_BLENDING_MULTIPLY
			outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_MIX )
			outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
		#elif defined( ENVMAP_BLENDING_ADD )
			outgoingLight += envColor.xyz * specularStrength * reflectivity;
		#endif
	#endif
#endif`,ax=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
#endif`,ox=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,lx=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,ux=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,cx=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,fx=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,dx=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,hx=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,px=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,mx=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,gx=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,_x=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,vx=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,xx=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, pow4( roughness ) ) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,Sx=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,yx=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,Mx=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,Ex=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,Tx=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.diffuseContribution = diffuseColor.rgb * ( 1.0 - metalnessFactor );
material.metalness = metalnessFactor;
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor;
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = vec3( 0.04 );
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.0001, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,wx=`uniform sampler2D dfgLUT;
struct PhysicalMaterial {
	vec3 diffuseColor;
	vec3 diffuseContribution;
	vec3 specularColor;
	vec3 specularColorBlended;
	float roughness;
	float metalness;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
		vec3 iridescenceFresnelDielectric;
		vec3 iridescenceFresnelMetallic;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return v;
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColorBlended;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transpose( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float rInv = 1.0 / ( roughness + 0.1 );
	float a = -1.9362 + 1.0678 * roughness + 0.4573 * r2 - 0.8469 * rInv;
	float b = -0.6014 + 0.5538 * roughness - 0.4670 * r2 - 0.1255 * rInv;
	float DG = exp( a * dotNV + b );
	return saturate( DG );
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
vec3 BRDF_GGX_Multiscatter( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 singleScatter = BRDF_GGX( lightDir, viewDir, normal, material );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 dfgV = texture2D( dfgLUT, vec2( material.roughness, dotNV ) ).rg;
	vec2 dfgL = texture2D( dfgLUT, vec2( material.roughness, dotNL ) ).rg;
	vec3 FssEss_V = material.specularColorBlended * dfgV.x + material.specularF90 * dfgV.y;
	vec3 FssEss_L = material.specularColorBlended * dfgL.x + material.specularF90 * dfgL.y;
	float Ess_V = dfgV.x + dfgV.y;
	float Ess_L = dfgL.x + dfgL.y;
	float Ems_V = 1.0 - Ess_V;
	float Ems_L = 1.0 - Ess_L;
	vec3 Favg = material.specularColorBlended + ( 1.0 - material.specularColorBlended ) * 0.047619;
	vec3 Fms = FssEss_V * FssEss_L * Favg / ( 1.0 - Ems_V * Ems_L * Favg + EPSILON );
	float compensationFactor = Ems_V * Ems_L;
	vec3 multiScatter = Fms * compensationFactor;
	return singleScatter + multiScatter;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColorBlended * t2.x + ( material.specularF90 - material.specularColorBlended ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseContribution * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
		#ifdef USE_CLEARCOAT
			vec3 Ncc = geometryClearcoatNormal;
			vec2 uvClearcoat = LTC_Uv( Ncc, viewDir, material.clearcoatRoughness );
			vec4 t1Clearcoat = texture2D( ltc_1, uvClearcoat );
			vec4 t2Clearcoat = texture2D( ltc_2, uvClearcoat );
			mat3 mInvClearcoat = mat3(
				vec3( t1Clearcoat.x, 0, t1Clearcoat.y ),
				vec3(             0, 1,             0 ),
				vec3( t1Clearcoat.z, 0, t1Clearcoat.w )
			);
			vec3 fresnelClearcoat = material.clearcoatF0 * t2Clearcoat.x + ( material.clearcoatF90 - material.clearcoatF0 ) * t2Clearcoat.y;
			clearcoatSpecularDirect += lightColor * fresnelClearcoat * LTC_Evaluate( Ncc, viewDir, position, mInvClearcoat, rectCoords );
		#endif
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
 
 		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
 
 		float sheenAlbedoV = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
 		float sheenAlbedoL = IBLSheenBRDF( geometryNormal, directLight.direction, material.sheenRoughness );
 
 		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * max( sheenAlbedoV, sheenAlbedoL );
 
 		irradiance *= sheenEnergyComp;
 
 	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX_Multiscatter( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 diffuse = irradiance * BRDF_Lambert( material.diffuseContribution );
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		diffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectDiffuse += diffuse;
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness ) * RECIPROCAL_PI;
 	#endif
	vec3 singleScatteringDielectric = vec3( 0.0 );
	vec3 multiScatteringDielectric = vec3( 0.0 );
	vec3 singleScatteringMetallic = vec3( 0.0 );
	vec3 multiScatteringMetallic = vec3( 0.0 );
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnelDielectric, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.iridescence, material.iridescenceFresnelMetallic, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscattering( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#endif
	vec3 singleScattering = mix( singleScatteringDielectric, singleScatteringMetallic, material.metalness );
	vec3 multiScattering = mix( multiScatteringDielectric, multiScatteringMetallic, material.metalness );
	vec3 totalScatteringDielectric = singleScatteringDielectric + multiScatteringDielectric;
	vec3 diffuse = material.diffuseContribution * ( 1.0 - totalScatteringDielectric );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	vec3 indirectSpecular = radiance * singleScattering;
	indirectSpecular += multiScattering * cosineWeightedIrradiance;
	vec3 indirectDiffuse = diffuse * cosineWeightedIrradiance;
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		indirectSpecular *= sheenEnergyComp;
		indirectDiffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectSpecular += indirectSpecular;
	reflectedLight.indirectDiffuse += indirectDiffuse;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,Ax=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnelDielectric = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceFresnelMetallic = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.diffuseColor );
		material.iridescenceFresnel = mix( material.iridescenceFresnelDielectric, material.iridescenceFresnelMetallic, material.metalness );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,Cx=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
		#if defined( STANDARD ) || defined( LAMBERT ) || defined( PHONG )
			iblIrradiance += getIBLIrradiance( geometryNormal );
		#endif
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,Rx=`#if defined( RE_IndirectDiffuse )
	#if defined( LAMBERT ) || defined( PHONG )
		irradiance += iblIrradiance;
	#endif
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,bx=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,Px=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,Dx=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,Lx=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,Nx=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,Ix=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Ux=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,Fx=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Ox=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,Bx=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,kx=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,zx=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Vx=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Hx=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,Gx=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Wx=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,Xx=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,jx=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Yx=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,qx=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,$x=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,Kx=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Zx=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Qx=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,Jx=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,eS=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,tS=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	#ifdef USE_REVERSED_DEPTH_BUFFER
	
		return depth * ( far - near ) - far;
	#else
		return depth * ( near - far ) - near;
	#endif
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	
	#ifdef USE_REVERSED_DEPTH_BUFFER
		return ( near * far ) / ( ( near - far ) * depth - near );
	#else
		return ( near * far ) / ( ( far - near ) * depth - far );
	#endif
}`,nS=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,iS=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,rS=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,sS=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,aS=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,oS=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,lS=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#else
			uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#endif
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#else
			uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#endif
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform samplerCubeShadow pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#elif defined( SHADOWMAP_TYPE_BASIC )
			uniform samplerCube pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#endif
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float interleavedGradientNoise( vec2 position ) {
			return fract( 52.9829189 * fract( dot( position, vec2( 0.06711056, 0.00583715 ) ) ) );
		}
		vec2 vogelDiskSample( int sampleIndex, int samplesCount, float phi ) {
			const float goldenAngle = 2.399963229728653;
			float r = sqrt( ( float( sampleIndex ) + 0.5 ) / float( samplesCount ) );
			float theta = float( sampleIndex ) * goldenAngle + phi;
			return vec2( cos( theta ), sin( theta ) ) * r;
		}
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float getShadow( sampler2DShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
				float radius = shadowRadius * texelSize.x;
				float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
				shadow = (
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 0, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 1, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 2, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 3, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 4, 5, phi ) * radius, shadowCoord.z ) )
				) * 0.2;
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#elif defined( SHADOWMAP_TYPE_VSM )
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 distribution = texture2D( shadowMap, shadowCoord.xy ).rg;
				float mean = distribution.x;
				float variance = distribution.y * distribution.y;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					float hard_shadow = step( mean, shadowCoord.z );
				#else
					float hard_shadow = step( shadowCoord.z, mean );
				#endif
				
				if ( hard_shadow == 1.0 ) {
					shadow = 1.0;
				} else {
					variance = max( variance, 0.0000001 );
					float d = shadowCoord.z - mean;
					float p_max = variance / ( variance + d * d );
					p_max = clamp( ( p_max - 0.3 ) / 0.65, 0.0, 1.0 );
					shadow = max( hard_shadow, p_max );
				}
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#else
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadowCoord.z -= shadowBias;
			#else
				shadowCoord.z += shadowBias;
			#endif
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				float depth = texture2D( shadowMap, shadowCoord.xy ).r;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					shadow = step( depth, shadowCoord.z );
				#else
					shadow = step( shadowCoord.z, depth );
				#endif
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	#if defined( SHADOWMAP_TYPE_PCF )
	float getPointShadow( samplerCubeShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 bd3D = normalize( lightToPosition );
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			#ifdef USE_REVERSED_DEPTH_BUFFER
				float dp = ( shadowCameraNear * ( shadowCameraFar - viewSpaceZ ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp -= shadowBias;
			#else
				float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp += shadowBias;
			#endif
			float texelSize = shadowRadius / shadowMapSize.x;
			vec3 absDir = abs( bd3D );
			vec3 tangent = absDir.x > absDir.z ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 );
			tangent = normalize( cross( bd3D, tangent ) );
			vec3 bitangent = cross( bd3D, tangent );
			float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;
			vec2 sample0 = vogelDiskSample( 0, 5, phi );
			vec2 sample1 = vogelDiskSample( 1, 5, phi );
			vec2 sample2 = vogelDiskSample( 2, 5, phi );
			vec2 sample3 = vogelDiskSample( 3, 5, phi );
			vec2 sample4 = vogelDiskSample( 4, 5, phi );
			shadow = (
				texture( shadowMap, vec4( bd3D + ( tangent * sample0.x + bitangent * sample0.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample1.x + bitangent * sample1.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample2.x + bitangent * sample2.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample3.x + bitangent * sample3.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample4.x + bitangent * sample4.y ) * texelSize, dp ) )
			) * 0.2;
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#elif defined( SHADOWMAP_TYPE_BASIC )
	float getPointShadow( samplerCube shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			float depth = textureCube( shadowMap, bd3D ).r;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				depth = 1.0 - depth;
			#endif
			shadow = step( dp, depth );
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#endif
	#endif
#endif`,uS=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,cS=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,fS=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0 && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,dS=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,hS=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,pS=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,mS=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,gS=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,_S=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,vS=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,xS=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,SS=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseContribution, material.specularColorBlended, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,yS=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,MS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,ES=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,TS=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,wS=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const AS=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,CS=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,RS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,bS=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,PS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,DS=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,LS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,NS=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,IS=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,US=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = vec4( dist, 0.0, 0.0, 1.0 );
}`,FS=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,OS=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,BS=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,kS=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,zS=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,VS=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,HS=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,GS=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,WS=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,XS=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,jS=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,YS=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( normalize( normal ) * 0.5 + 0.5, diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,qS=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,$S=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,KS=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,ZS=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
 
		outgoingLight = outgoingLight + sheenSpecularDirect + sheenSpecularIndirect;
 
 	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,QS=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,JS=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,ey=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,ty=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,ny=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,iy=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,ry=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,sy=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,dt={alphahash_fragment:Cv,alphahash_pars_fragment:Rv,alphamap_fragment:bv,alphamap_pars_fragment:Pv,alphatest_fragment:Dv,alphatest_pars_fragment:Lv,aomap_fragment:Nv,aomap_pars_fragment:Iv,batching_pars_vertex:Uv,batching_vertex:Fv,begin_vertex:Ov,beginnormal_vertex:Bv,bsdfs:kv,iridescence_fragment:zv,bumpmap_pars_fragment:Vv,clipping_planes_fragment:Hv,clipping_planes_pars_fragment:Gv,clipping_planes_pars_vertex:Wv,clipping_planes_vertex:Xv,color_fragment:jv,color_pars_fragment:Yv,color_pars_vertex:qv,color_vertex:$v,common:Kv,cube_uv_reflection_fragment:Zv,defaultnormal_vertex:Qv,displacementmap_pars_vertex:Jv,displacementmap_vertex:ex,emissivemap_fragment:tx,emissivemap_pars_fragment:nx,colorspace_fragment:ix,colorspace_pars_fragment:rx,envmap_fragment:sx,envmap_common_pars_fragment:ax,envmap_pars_fragment:ox,envmap_pars_vertex:lx,envmap_physical_pars_fragment:xx,envmap_vertex:ux,fog_vertex:cx,fog_pars_vertex:fx,fog_fragment:dx,fog_pars_fragment:hx,gradientmap_pars_fragment:px,lightmap_pars_fragment:mx,lights_lambert_fragment:gx,lights_lambert_pars_fragment:_x,lights_pars_begin:vx,lights_toon_fragment:Sx,lights_toon_pars_fragment:yx,lights_phong_fragment:Mx,lights_phong_pars_fragment:Ex,lights_physical_fragment:Tx,lights_physical_pars_fragment:wx,lights_fragment_begin:Ax,lights_fragment_maps:Cx,lights_fragment_end:Rx,logdepthbuf_fragment:bx,logdepthbuf_pars_fragment:Px,logdepthbuf_pars_vertex:Dx,logdepthbuf_vertex:Lx,map_fragment:Nx,map_pars_fragment:Ix,map_particle_fragment:Ux,map_particle_pars_fragment:Fx,metalnessmap_fragment:Ox,metalnessmap_pars_fragment:Bx,morphinstance_vertex:kx,morphcolor_vertex:zx,morphnormal_vertex:Vx,morphtarget_pars_vertex:Hx,morphtarget_vertex:Gx,normal_fragment_begin:Wx,normal_fragment_maps:Xx,normal_pars_fragment:jx,normal_pars_vertex:Yx,normal_vertex:qx,normalmap_pars_fragment:$x,clearcoat_normal_fragment_begin:Kx,clearcoat_normal_fragment_maps:Zx,clearcoat_pars_fragment:Qx,iridescence_pars_fragment:Jx,opaque_fragment:eS,packing:tS,premultiplied_alpha_fragment:nS,project_vertex:iS,dithering_fragment:rS,dithering_pars_fragment:sS,roughnessmap_fragment:aS,roughnessmap_pars_fragment:oS,shadowmap_pars_fragment:lS,shadowmap_pars_vertex:uS,shadowmap_vertex:cS,shadowmask_pars_fragment:fS,skinbase_vertex:dS,skinning_pars_vertex:hS,skinning_vertex:pS,skinnormal_vertex:mS,specularmap_fragment:gS,specularmap_pars_fragment:_S,tonemapping_fragment:vS,tonemapping_pars_fragment:xS,transmission_fragment:SS,transmission_pars_fragment:yS,uv_pars_fragment:MS,uv_pars_vertex:ES,uv_vertex:TS,worldpos_vertex:wS,background_vert:AS,background_frag:CS,backgroundCube_vert:RS,backgroundCube_frag:bS,cube_vert:PS,cube_frag:DS,depth_vert:LS,depth_frag:NS,distance_vert:IS,distance_frag:US,equirect_vert:FS,equirect_frag:OS,linedashed_vert:BS,linedashed_frag:kS,meshbasic_vert:zS,meshbasic_frag:VS,meshlambert_vert:HS,meshlambert_frag:GS,meshmatcap_vert:WS,meshmatcap_frag:XS,meshnormal_vert:jS,meshnormal_frag:YS,meshphong_vert:qS,meshphong_frag:$S,meshphysical_vert:KS,meshphysical_frag:ZS,meshtoon_vert:QS,meshtoon_frag:JS,points_vert:ey,points_frag:ty,shadow_vert:ny,shadow_frag:iy,sprite_vert:ry,sprite_frag:sy},Pe={common:{diffuse:{value:new bt(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new ft},alphaMap:{value:null},alphaMapTransform:{value:new ft},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new ft}},envmap:{envMap:{value:null},envMapRotation:{value:new ft},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98},dfgLUT:{value:null}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new ft}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new ft}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new ft},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new ft},normalScale:{value:new Lt(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new ft},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new ft}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new ft}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new ft}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new bt(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new bt(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new ft},alphaTest:{value:0},uvTransform:{value:new ft}},sprite:{diffuse:{value:new bt(16777215)},opacity:{value:1},center:{value:new Lt(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new ft},alphaMap:{value:null},alphaMapTransform:{value:new ft},alphaTest:{value:0}}},Ti={basic:{uniforms:Mn([Pe.common,Pe.specularmap,Pe.envmap,Pe.aomap,Pe.lightmap,Pe.fog]),vertexShader:dt.meshbasic_vert,fragmentShader:dt.meshbasic_frag},lambert:{uniforms:Mn([Pe.common,Pe.specularmap,Pe.envmap,Pe.aomap,Pe.lightmap,Pe.emissivemap,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,Pe.fog,Pe.lights,{emissive:{value:new bt(0)},envMapIntensity:{value:1}}]),vertexShader:dt.meshlambert_vert,fragmentShader:dt.meshlambert_frag},phong:{uniforms:Mn([Pe.common,Pe.specularmap,Pe.envmap,Pe.aomap,Pe.lightmap,Pe.emissivemap,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,Pe.fog,Pe.lights,{emissive:{value:new bt(0)},specular:{value:new bt(1118481)},shininess:{value:30},envMapIntensity:{value:1}}]),vertexShader:dt.meshphong_vert,fragmentShader:dt.meshphong_frag},standard:{uniforms:Mn([Pe.common,Pe.envmap,Pe.aomap,Pe.lightmap,Pe.emissivemap,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,Pe.roughnessmap,Pe.metalnessmap,Pe.fog,Pe.lights,{emissive:{value:new bt(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:dt.meshphysical_vert,fragmentShader:dt.meshphysical_frag},toon:{uniforms:Mn([Pe.common,Pe.aomap,Pe.lightmap,Pe.emissivemap,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,Pe.gradientmap,Pe.fog,Pe.lights,{emissive:{value:new bt(0)}}]),vertexShader:dt.meshtoon_vert,fragmentShader:dt.meshtoon_frag},matcap:{uniforms:Mn([Pe.common,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,Pe.fog,{matcap:{value:null}}]),vertexShader:dt.meshmatcap_vert,fragmentShader:dt.meshmatcap_frag},points:{uniforms:Mn([Pe.points,Pe.fog]),vertexShader:dt.points_vert,fragmentShader:dt.points_frag},dashed:{uniforms:Mn([Pe.common,Pe.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:dt.linedashed_vert,fragmentShader:dt.linedashed_frag},depth:{uniforms:Mn([Pe.common,Pe.displacementmap]),vertexShader:dt.depth_vert,fragmentShader:dt.depth_frag},normal:{uniforms:Mn([Pe.common,Pe.bumpmap,Pe.normalmap,Pe.displacementmap,{opacity:{value:1}}]),vertexShader:dt.meshnormal_vert,fragmentShader:dt.meshnormal_frag},sprite:{uniforms:Mn([Pe.sprite,Pe.fog]),vertexShader:dt.sprite_vert,fragmentShader:dt.sprite_frag},background:{uniforms:{uvTransform:{value:new ft},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:dt.background_vert,fragmentShader:dt.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new ft}},vertexShader:dt.backgroundCube_vert,fragmentShader:dt.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:dt.cube_vert,fragmentShader:dt.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:dt.equirect_vert,fragmentShader:dt.equirect_frag},distance:{uniforms:Mn([Pe.common,Pe.displacementmap,{referencePosition:{value:new ne},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:dt.distance_vert,fragmentShader:dt.distance_frag},shadow:{uniforms:Mn([Pe.lights,Pe.fog,{color:{value:new bt(0)},opacity:{value:1}}]),vertexShader:dt.shadow_vert,fragmentShader:dt.shadow_frag}};Ti.physical={uniforms:Mn([Ti.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new ft},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new ft},clearcoatNormalScale:{value:new Lt(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new ft},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new ft},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new ft},sheen:{value:0},sheenColor:{value:new bt(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new ft},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new ft},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new ft},transmissionSamplerSize:{value:new Lt},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new ft},attenuationDistance:{value:0},attenuationColor:{value:new bt(0)},specularColor:{value:new bt(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new ft},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new ft},anisotropyVector:{value:new Lt},anisotropyMap:{value:null},anisotropyMapTransform:{value:new ft}}]),vertexShader:dt.meshphysical_vert,fragmentShader:dt.meshphysical_frag};const wl={r:0,b:0,g:0},qr=new Qi,ay=new $t;function oy(s,e,n,r,o,u){const c=new bt(0);let d=o===!0?0:1,p,m,x=null,S=0,g=null;function y(R){let L=R.isScene===!0?R.background:null;if(L&&L.isTexture){const b=R.backgroundBlurriness>0;L=e.get(L,b)}return L}function M(R){let L=!1;const b=y(R);b===null?_(c,d):b&&b.isColor&&(_(b,1),L=!0);const F=s.xr.getEnvironmentBlendMode();F==="additive"?n.buffers.color.setClear(0,0,0,1,u):F==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,u),(s.autoClear||L)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),s.clear(s.autoClearColor,s.autoClearDepth,s.autoClearStencil))}function C(R,L){const b=y(L);b&&(b.isCubeTexture||b.mapping===Bl)?(m===void 0&&(m=new ii(new ja(1,1,1),new Di({name:"BackgroundCubeMaterial",uniforms:js(Ti.backgroundCube.uniforms),vertexShader:Ti.backgroundCube.vertexShader,fragmentShader:Ti.backgroundCube.fragmentShader,side:In,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),m.geometry.deleteAttribute("normal"),m.geometry.deleteAttribute("uv"),m.onBeforeRender=function(F,U,z){this.matrixWorld.copyPosition(z.matrixWorld)},Object.defineProperty(m.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),r.update(m)),qr.copy(L.backgroundRotation),qr.x*=-1,qr.y*=-1,qr.z*=-1,b.isCubeTexture&&b.isRenderTargetTexture===!1&&(qr.y*=-1,qr.z*=-1),m.material.uniforms.envMap.value=b,m.material.uniforms.flipEnvMap.value=b.isCubeTexture&&b.isRenderTargetTexture===!1?-1:1,m.material.uniforms.backgroundBlurriness.value=L.backgroundBlurriness,m.material.uniforms.backgroundIntensity.value=L.backgroundIntensity,m.material.uniforms.backgroundRotation.value.setFromMatrix4(ay.makeRotationFromEuler(qr)),m.material.toneMapped=Et.getTransfer(b.colorSpace)!==Dt,(x!==b||S!==b.version||g!==s.toneMapping)&&(m.material.needsUpdate=!0,x=b,S=b.version,g=s.toneMapping),m.layers.enableAll(),R.unshift(m,m.geometry,m.material,0,0,null)):b&&b.isTexture&&(p===void 0&&(p=new ii(new zl(2,2),new Di({name:"BackgroundMaterial",uniforms:js(Ti.background.uniforms),vertexShader:Ti.background.vertexShader,fragmentShader:Ti.background.fragmentShader,side:Rr,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),p.geometry.deleteAttribute("normal"),Object.defineProperty(p.material,"map",{get:function(){return this.uniforms.t2D.value}}),r.update(p)),p.material.uniforms.t2D.value=b,p.material.uniforms.backgroundIntensity.value=L.backgroundIntensity,p.material.toneMapped=Et.getTransfer(b.colorSpace)!==Dt,b.matrixAutoUpdate===!0&&b.updateMatrix(),p.material.uniforms.uvTransform.value.copy(b.matrix),(x!==b||S!==b.version||g!==s.toneMapping)&&(p.material.needsUpdate=!0,x=b,S=b.version,g=s.toneMapping),p.layers.enableAll(),R.unshift(p,p.geometry,p.material,0,0,null))}function _(R,L){R.getRGB(wl,ug(s)),n.buffers.color.setClear(wl.r,wl.g,wl.b,L,u)}function v(){m!==void 0&&(m.geometry.dispose(),m.material.dispose(),m=void 0),p!==void 0&&(p.geometry.dispose(),p.material.dispose(),p=void 0)}return{getClearColor:function(){return c},setClearColor:function(R,L=1){c.set(R),d=L,_(c,d)},getClearAlpha:function(){return d},setClearAlpha:function(R){d=R,_(c,d)},render:M,addToRenderList:C,dispose:v}}function ly(s,e){const n=s.getParameter(s.MAX_VERTEX_ATTRIBS),r={},o=g(null);let u=o,c=!1;function d(O,te,Q,oe,K){let ee=!1;const W=S(O,oe,Q,te);u!==W&&(u=W,m(u.object)),ee=y(O,oe,Q,K),ee&&M(O,oe,Q,K),K!==null&&e.update(K,s.ELEMENT_ARRAY_BUFFER),(ee||c)&&(c=!1,b(O,te,Q,oe),K!==null&&s.bindBuffer(s.ELEMENT_ARRAY_BUFFER,e.get(K).buffer))}function p(){return s.createVertexArray()}function m(O){return s.bindVertexArray(O)}function x(O){return s.deleteVertexArray(O)}function S(O,te,Q,oe){const K=oe.wireframe===!0;let ee=r[te.id];ee===void 0&&(ee={},r[te.id]=ee);const W=O.isInstancedMesh===!0?O.id:0;let q=ee[W];q===void 0&&(q={},ee[W]=q);let ae=q[Q.id];ae===void 0&&(ae={},q[Q.id]=ae);let le=ae[K];return le===void 0&&(le=g(p()),ae[K]=le),le}function g(O){const te=[],Q=[],oe=[];for(let K=0;K<n;K++)te[K]=0,Q[K]=0,oe[K]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:te,enabledAttributes:Q,attributeDivisors:oe,object:O,attributes:{},index:null}}function y(O,te,Q,oe){const K=u.attributes,ee=te.attributes;let W=0;const q=Q.getAttributes();for(const ae in q)if(q[ae].location>=0){const I=K[ae];let j=ee[ae];if(j===void 0&&(ae==="instanceMatrix"&&O.instanceMatrix&&(j=O.instanceMatrix),ae==="instanceColor"&&O.instanceColor&&(j=O.instanceColor)),I===void 0||I.attribute!==j||j&&I.data!==j.data)return!0;W++}return u.attributesNum!==W||u.index!==oe}function M(O,te,Q,oe){const K={},ee=te.attributes;let W=0;const q=Q.getAttributes();for(const ae in q)if(q[ae].location>=0){let I=ee[ae];I===void 0&&(ae==="instanceMatrix"&&O.instanceMatrix&&(I=O.instanceMatrix),ae==="instanceColor"&&O.instanceColor&&(I=O.instanceColor));const j={};j.attribute=I,I&&I.data&&(j.data=I.data),K[ae]=j,W++}u.attributes=K,u.attributesNum=W,u.index=oe}function C(){const O=u.newAttributes;for(let te=0,Q=O.length;te<Q;te++)O[te]=0}function _(O){v(O,0)}function v(O,te){const Q=u.newAttributes,oe=u.enabledAttributes,K=u.attributeDivisors;Q[O]=1,oe[O]===0&&(s.enableVertexAttribArray(O),oe[O]=1),K[O]!==te&&(s.vertexAttribDivisor(O,te),K[O]=te)}function R(){const O=u.newAttributes,te=u.enabledAttributes;for(let Q=0,oe=te.length;Q<oe;Q++)te[Q]!==O[Q]&&(s.disableVertexAttribArray(Q),te[Q]=0)}function L(O,te,Q,oe,K,ee,W){W===!0?s.vertexAttribIPointer(O,te,Q,K,ee):s.vertexAttribPointer(O,te,Q,oe,K,ee)}function b(O,te,Q,oe){C();const K=oe.attributes,ee=Q.getAttributes(),W=te.defaultAttributeValues;for(const q in ee){const ae=ee[q];if(ae.location>=0){let le=K[q];if(le===void 0&&(q==="instanceMatrix"&&O.instanceMatrix&&(le=O.instanceMatrix),q==="instanceColor"&&O.instanceColor&&(le=O.instanceColor)),le!==void 0){const I=le.normalized,j=le.itemSize,Ce=e.get(le);if(Ce===void 0)continue;const Xe=Ce.buffer,Ze=Ce.type,ie=Ce.bytesPerElement,me=Ze===s.INT||Ze===s.UNSIGNED_INT||le.gpuType===td;if(le.isInterleavedBufferAttribute){const pe=le.data,Fe=pe.stride,He=le.offset;if(pe.isInstancedInterleavedBuffer){for(let nt=0;nt<ae.locationSize;nt++)v(ae.location+nt,pe.meshPerAttribute);O.isInstancedMesh!==!0&&oe._maxInstanceCount===void 0&&(oe._maxInstanceCount=pe.meshPerAttribute*pe.count)}else for(let nt=0;nt<ae.locationSize;nt++)_(ae.location+nt);s.bindBuffer(s.ARRAY_BUFFER,Xe);for(let nt=0;nt<ae.locationSize;nt++)L(ae.location+nt,j/ae.locationSize,Ze,I,Fe*ie,(He+j/ae.locationSize*nt)*ie,me)}else{if(le.isInstancedBufferAttribute){for(let pe=0;pe<ae.locationSize;pe++)v(ae.location+pe,le.meshPerAttribute);O.isInstancedMesh!==!0&&oe._maxInstanceCount===void 0&&(oe._maxInstanceCount=le.meshPerAttribute*le.count)}else for(let pe=0;pe<ae.locationSize;pe++)_(ae.location+pe);s.bindBuffer(s.ARRAY_BUFFER,Xe);for(let pe=0;pe<ae.locationSize;pe++)L(ae.location+pe,j/ae.locationSize,Ze,I,j*ie,j/ae.locationSize*pe*ie,me)}}else if(W!==void 0){const I=W[q];if(I!==void 0)switch(I.length){case 2:s.vertexAttrib2fv(ae.location,I);break;case 3:s.vertexAttrib3fv(ae.location,I);break;case 4:s.vertexAttrib4fv(ae.location,I);break;default:s.vertexAttrib1fv(ae.location,I)}}}}R()}function F(){D();for(const O in r){const te=r[O];for(const Q in te){const oe=te[Q];for(const K in oe){const ee=oe[K];for(const W in ee)x(ee[W].object),delete ee[W];delete oe[K]}}delete r[O]}}function U(O){if(r[O.id]===void 0)return;const te=r[O.id];for(const Q in te){const oe=te[Q];for(const K in oe){const ee=oe[K];for(const W in ee)x(ee[W].object),delete ee[W];delete oe[K]}}delete r[O.id]}function z(O){for(const te in r){const Q=r[te];for(const oe in Q){const K=Q[oe];if(K[O.id]===void 0)continue;const ee=K[O.id];for(const W in ee)x(ee[W].object),delete ee[W];delete K[O.id]}}}function A(O){for(const te in r){const Q=r[te],oe=O.isInstancedMesh===!0?O.id:0,K=Q[oe];if(K!==void 0){for(const ee in K){const W=K[ee];for(const q in W)x(W[q].object),delete W[q];delete K[ee]}delete Q[oe],Object.keys(Q).length===0&&delete r[te]}}}function D(){fe(),c=!0,u!==o&&(u=o,m(u.object))}function fe(){o.geometry=null,o.program=null,o.wireframe=!1}return{setup:d,reset:D,resetDefaultState:fe,dispose:F,releaseStatesOfGeometry:U,releaseStatesOfObject:A,releaseStatesOfProgram:z,initAttributes:C,enableAttribute:_,disableUnusedAttributes:R}}function uy(s,e,n){let r;function o(m){r=m}function u(m,x){s.drawArrays(r,m,x),n.update(x,r,1)}function c(m,x,S){S!==0&&(s.drawArraysInstanced(r,m,x,S),n.update(x,r,S))}function d(m,x,S){if(S===0)return;e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(r,m,0,x,0,S);let y=0;for(let M=0;M<S;M++)y+=x[M];n.update(y,r,1)}function p(m,x,S,g){if(S===0)return;const y=e.get("WEBGL_multi_draw");if(y===null)for(let M=0;M<m.length;M++)c(m[M],x[M],g[M]);else{y.multiDrawArraysInstancedWEBGL(r,m,0,x,0,g,0,S);let M=0;for(let C=0;C<S;C++)M+=x[C]*g[C];n.update(M,r,1)}}this.setMode=o,this.render=u,this.renderInstances=c,this.renderMultiDraw=d,this.renderMultiDrawInstances=p}function cy(s,e,n,r){let o;function u(){if(o!==void 0)return o;if(e.has("EXT_texture_filter_anisotropic")===!0){const z=e.get("EXT_texture_filter_anisotropic");o=s.getParameter(z.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else o=0;return o}function c(z){return!(z!==mi&&r.convert(z)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_FORMAT))}function d(z){const A=z===Ki&&(e.has("EXT_color_buffer_half_float")||e.has("EXT_color_buffer_float"));return!(z!==ni&&r.convert(z)!==s.getParameter(s.IMPLEMENTATION_COLOR_READ_TYPE)&&z!==Ai&&!A)}function p(z){if(z==="highp"){if(s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.HIGH_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.HIGH_FLOAT).precision>0)return"highp";z="mediump"}return z==="mediump"&&s.getShaderPrecisionFormat(s.VERTEX_SHADER,s.MEDIUM_FLOAT).precision>0&&s.getShaderPrecisionFormat(s.FRAGMENT_SHADER,s.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let m=n.precision!==void 0?n.precision:"highp";const x=p(m);x!==m&&(ot("WebGLRenderer:",m,"not supported, using",x,"instead."),m=x);const S=n.logarithmicDepthBuffer===!0,g=n.reversedDepthBuffer===!0&&e.has("EXT_clip_control"),y=s.getParameter(s.MAX_TEXTURE_IMAGE_UNITS),M=s.getParameter(s.MAX_VERTEX_TEXTURE_IMAGE_UNITS),C=s.getParameter(s.MAX_TEXTURE_SIZE),_=s.getParameter(s.MAX_CUBE_MAP_TEXTURE_SIZE),v=s.getParameter(s.MAX_VERTEX_ATTRIBS),R=s.getParameter(s.MAX_VERTEX_UNIFORM_VECTORS),L=s.getParameter(s.MAX_VARYING_VECTORS),b=s.getParameter(s.MAX_FRAGMENT_UNIFORM_VECTORS),F=s.getParameter(s.MAX_SAMPLES),U=s.getParameter(s.SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:u,getMaxPrecision:p,textureFormatReadable:c,textureTypeReadable:d,precision:m,logarithmicDepthBuffer:S,reversedDepthBuffer:g,maxTextures:y,maxVertexTextures:M,maxTextureSize:C,maxCubemapSize:_,maxAttributes:v,maxVertexUniforms:R,maxVaryings:L,maxFragmentUniforms:b,maxSamples:F,samples:U}}function fy(s){const e=this;let n=null,r=0,o=!1,u=!1;const c=new Kr,d=new ft,p={value:null,needsUpdate:!1};this.uniform=p,this.numPlanes=0,this.numIntersection=0,this.init=function(S,g){const y=S.length!==0||g||r!==0||o;return o=g,r=S.length,y},this.beginShadows=function(){u=!0,x(null)},this.endShadows=function(){u=!1},this.setGlobalState=function(S,g){n=x(S,g,0)},this.setState=function(S,g,y){const M=S.clippingPlanes,C=S.clipIntersection,_=S.clipShadows,v=s.get(S);if(!o||M===null||M.length===0||u&&!_)u?x(null):m();else{const R=u?0:r,L=R*4;let b=v.clippingState||null;p.value=b,b=x(M,g,L,y);for(let F=0;F!==L;++F)b[F]=n[F];v.clippingState=b,this.numIntersection=C?this.numPlanes:0,this.numPlanes+=R}};function m(){p.value!==n&&(p.value=n,p.needsUpdate=r>0),e.numPlanes=r,e.numIntersection=0}function x(S,g,y,M){const C=S!==null?S.length:0;let _=null;if(C!==0){if(_=p.value,M!==!0||_===null){const v=y+C*4,R=g.matrixWorldInverse;d.getNormalMatrix(R),(_===null||_.length<v)&&(_=new Float32Array(v));for(let L=0,b=y;L!==C;++L,b+=4)c.copy(S[L]).applyMatrix4(R,d),c.normal.toArray(_,b),_[b+3]=c.constant}p.value=_,p.needsUpdate=!0}return e.numPlanes=C,e.numIntersection=0,_}}const Cr=4,dm=[.125,.215,.35,.446,.526,.582],Qr=20,dy=256,Ua=new fg,hm=new bt;let Jc=null,ef=0,tf=0,nf=!1;const hy=new ne;class pm{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._sizeLods=[],this._sigmas=[],this._lodMeshes=[],this._backgroundBox=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._blurMaterial=null,this._ggxMaterial=null}fromScene(e,n=0,r=.1,o=100,u={}){const{size:c=256,position:d=hy}=u;Jc=this._renderer.getRenderTarget(),ef=this._renderer.getActiveCubeFace(),tf=this._renderer.getActiveMipmapLevel(),nf=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(c);const p=this._allocateTargets();return p.depthBuffer=!0,this._sceneToCubeUV(e,r,o,p,d),n>0&&this._blur(p,0,0,n),this._applyPMREM(p),this._cleanup(p),p}fromEquirectangular(e,n=null){return this._fromTexture(e,n)}fromCubemap(e,n=null){return this._fromTexture(e,n)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=_m(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=gm(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose(),this._backgroundBox!==null&&(this._backgroundBox.geometry.dispose(),this._backgroundBox.material.dispose())}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._ggxMaterial!==null&&this._ggxMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodMeshes.length;e++)this._lodMeshes[e].geometry.dispose()}_cleanup(e){this._renderer.setRenderTarget(Jc,ef,tf),this._renderer.xr.enabled=nf,e.scissorTest=!1,ks(e,0,0,e.width,e.height)}_fromTexture(e,n){e.mapping===ts||e.mapping===Gs?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),Jc=this._renderer.getRenderTarget(),ef=this._renderer.getActiveCubeFace(),tf=this._renderer.getActiveMipmapLevel(),nf=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;const r=n||this._allocateTargets();return this._textureToCubeUV(e,r),this._applyPMREM(r),this._cleanup(r),r}_allocateTargets(){const e=3*Math.max(this._cubeSize,112),n=4*this._cubeSize,r={magFilter:_n,minFilter:_n,generateMipmaps:!1,type:Ki,format:mi,colorSpace:Xs,depthBuffer:!1},o=mm(e,n,r);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==n){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=mm(e,n,r);const{_lodMax:u}=this;({lodMeshes:this._lodMeshes,sizeLods:this._sizeLods,sigmas:this._sigmas}=py(u)),this._blurMaterial=gy(u,e,n),this._ggxMaterial=my(u,e,n)}return o}_compileMaterial(e){const n=new ii(new Gn,e);this._renderer.compile(n,Ua)}_sceneToCubeUV(e,n,r,o,u){const p=new ti(90,1,n,r),m=[1,-1,1,1,1,1],x=[1,1,1,-1,-1,-1],S=this._renderer,g=S.autoClear,y=S.toneMapping;S.getClearColor(hm),S.toneMapping=Ri,S.autoClear=!1,S.state.buffers.depth.getReversed()&&(S.setRenderTarget(o),S.clearDepth(),S.setRenderTarget(null)),this._backgroundBox===null&&(this._backgroundBox=new ii(new ja,new ka({name:"PMREM.Background",side:In,depthWrite:!1,depthTest:!1})));const C=this._backgroundBox,_=C.material;let v=!1;const R=e.background;R?R.isColor&&(_.color.copy(R),e.background=null,v=!0):(_.color.copy(hm),v=!0);for(let L=0;L<6;L++){const b=L%3;b===0?(p.up.set(0,m[L],0),p.position.set(u.x,u.y,u.z),p.lookAt(u.x+x[L],u.y,u.z)):b===1?(p.up.set(0,0,m[L]),p.position.set(u.x,u.y,u.z),p.lookAt(u.x,u.y+x[L],u.z)):(p.up.set(0,m[L],0),p.position.set(u.x,u.y,u.z),p.lookAt(u.x,u.y,u.z+x[L]));const F=this._cubeSize;ks(o,b*F,L>2?F:0,F,F),S.setRenderTarget(o),v&&S.render(C,p),S.render(e,p)}S.toneMapping=y,S.autoClear=g,e.background=R}_textureToCubeUV(e,n){const r=this._renderer,o=e.mapping===ts||e.mapping===Gs;o?(this._cubemapMaterial===null&&(this._cubemapMaterial=_m()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=gm());const u=o?this._cubemapMaterial:this._equirectMaterial,c=this._lodMeshes[0];c.material=u;const d=u.uniforms;d.envMap.value=e;const p=this._cubeSize;ks(n,0,0,3*p,2*p),r.setRenderTarget(n),r.render(c,Ua)}_applyPMREM(e){const n=this._renderer,r=n.autoClear;n.autoClear=!1;const o=this._lodMeshes.length;for(let u=1;u<o;u++)this._applyGGXFilter(e,u-1,u);n.autoClear=r}_applyGGXFilter(e,n,r){const o=this._renderer,u=this._pingPongRenderTarget,c=this._ggxMaterial,d=this._lodMeshes[r];d.material=c;const p=c.uniforms,m=r/(this._lodMeshes.length-1),x=n/(this._lodMeshes.length-1),S=Math.sqrt(m*m-x*x),g=0+m*1.25,y=S*g,{_lodMax:M}=this,C=this._sizeLods[r],_=3*C*(r>M-Cr?r-M+Cr:0),v=4*(this._cubeSize-C);p.envMap.value=e.texture,p.roughness.value=y,p.mipInt.value=M-n,ks(u,_,v,3*C,2*C),o.setRenderTarget(u),o.render(d,Ua),p.envMap.value=u.texture,p.roughness.value=0,p.mipInt.value=M-r,ks(e,_,v,3*C,2*C),o.setRenderTarget(e),o.render(d,Ua)}_blur(e,n,r,o,u){const c=this._pingPongRenderTarget;this._halfBlur(e,c,n,r,o,"latitudinal",u),this._halfBlur(c,e,r,r,o,"longitudinal",u)}_halfBlur(e,n,r,o,u,c,d){const p=this._renderer,m=this._blurMaterial;c!=="latitudinal"&&c!=="longitudinal"&&wt("blur direction must be either latitudinal or longitudinal!");const x=3,S=this._lodMeshes[o];S.material=m;const g=m.uniforms,y=this._sizeLods[r]-1,M=isFinite(u)?Math.PI/(2*y):2*Math.PI/(2*Qr-1),C=u/M,_=isFinite(u)?1+Math.floor(x*C):Qr;_>Qr&&ot(`sigmaRadians, ${u}, is too large and will clip, as it requested ${_} samples when the maximum is set to ${Qr}`);const v=[];let R=0;for(let z=0;z<Qr;++z){const A=z/C,D=Math.exp(-A*A/2);v.push(D),z===0?R+=D:z<_&&(R+=2*D)}for(let z=0;z<v.length;z++)v[z]=v[z]/R;g.envMap.value=e.texture,g.samples.value=_,g.weights.value=v,g.latitudinal.value=c==="latitudinal",d&&(g.poleAxis.value=d);const{_lodMax:L}=this;g.dTheta.value=M,g.mipInt.value=L-r;const b=this._sizeLods[o],F=3*b*(o>L-Cr?o-L+Cr:0),U=4*(this._cubeSize-b);ks(n,F,U,3*b,2*b),p.setRenderTarget(n),p.render(S,Ua)}}function py(s){const e=[],n=[],r=[];let o=s;const u=s-Cr+1+dm.length;for(let c=0;c<u;c++){const d=Math.pow(2,o);e.push(d);let p=1/d;c>s-Cr?p=dm[c-s+Cr-1]:c===0&&(p=0),n.push(p);const m=1/(d-2),x=-m,S=1+m,g=[x,x,S,x,S,S,x,x,S,S,x,S],y=6,M=6,C=3,_=2,v=1,R=new Float32Array(C*M*y),L=new Float32Array(_*M*y),b=new Float32Array(v*M*y);for(let U=0;U<y;U++){const z=U%3*2/3-1,A=U>2?0:-1,D=[z,A,0,z+2/3,A,0,z+2/3,A+1,0,z,A,0,z+2/3,A+1,0,z,A+1,0];R.set(D,C*M*U),L.set(g,_*M*U);const fe=[U,U,U,U,U,U];b.set(fe,v*M*U)}const F=new Gn;F.setAttribute("position",new gi(R,C)),F.setAttribute("uv",new gi(L,_)),F.setAttribute("faceIndex",new gi(b,v)),r.push(new ii(F,null)),o>Cr&&o--}return{lodMeshes:r,sizeLods:e,sigmas:n}}function mm(s,e,n){const r=new bi(s,e,n);return r.texture.mapping=Bl,r.texture.name="PMREM.cubeUv",r.scissorTest=!0,r}function ks(s,e,n,r,o){s.viewport.set(e,n,r,o),s.scissor.set(e,n,r,o)}function my(s,e,n){return new Di({name:"PMREMGGXConvolution",defines:{GGX_SAMPLES:dy,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/n,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},roughness:{value:0},mipInt:{value:0}},vertexShader:Vl(),fragmentShader:`

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float roughness;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359

			// Van der Corput radical inverse
			float radicalInverse_VdC(uint bits) {
				bits = (bits << 16u) | (bits >> 16u);
				bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
				bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
				bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
				bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
				return float(bits) * 2.3283064365386963e-10; // / 0x100000000
			}

			// Hammersley sequence
			vec2 hammersley(uint i, uint N) {
				return vec2(float(i) / float(N), radicalInverse_VdC(i));
			}

			// GGX VNDF importance sampling (Eric Heitz 2018)
			// "Sampling the GGX Distribution of Visible Normals"
			// https://jcgt.org/published/0007/04/01/
			vec3 importanceSampleGGX_VNDF(vec2 Xi, vec3 V, float roughness) {
				float alpha = roughness * roughness;

				// Section 4.1: Orthonormal basis
				vec3 T1 = vec3(1.0, 0.0, 0.0);
				vec3 T2 = cross(V, T1);

				// Section 4.2: Parameterization of projected area
				float r = sqrt(Xi.x);
				float phi = 2.0 * PI * Xi.y;
				float t1 = r * cos(phi);
				float t2 = r * sin(phi);
				float s = 0.5 * (1.0 + V.z);
				t2 = (1.0 - s) * sqrt(1.0 - t1 * t1) + s * t2;

				// Section 4.3: Reprojection onto hemisphere
				vec3 Nh = t1 * T1 + t2 * T2 + sqrt(max(0.0, 1.0 - t1 * t1 - t2 * t2)) * V;

				// Section 3.4: Transform back to ellipsoid configuration
				return normalize(vec3(alpha * Nh.x, alpha * Nh.y, max(0.0, Nh.z)));
			}

			void main() {
				vec3 N = normalize(vOutputDirection);
				vec3 V = N; // Assume view direction equals normal for pre-filtering

				vec3 prefilteredColor = vec3(0.0);
				float totalWeight = 0.0;

				// For very low roughness, just sample the environment directly
				if (roughness < 0.001) {
					gl_FragColor = vec4(bilinearCubeUV(envMap, N, mipInt), 1.0);
					return;
				}

				// Tangent space basis for VNDF sampling
				vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
				vec3 tangent = normalize(cross(up, N));
				vec3 bitangent = cross(N, tangent);

				for(uint i = 0u; i < uint(GGX_SAMPLES); i++) {
					vec2 Xi = hammersley(i, uint(GGX_SAMPLES));

					// For PMREM, V = N, so in tangent space V is always (0, 0, 1)
					vec3 H_tangent = importanceSampleGGX_VNDF(Xi, vec3(0.0, 0.0, 1.0), roughness);

					// Transform H back to world space
					vec3 H = normalize(tangent * H_tangent.x + bitangent * H_tangent.y + N * H_tangent.z);
					vec3 L = normalize(2.0 * dot(V, H) * H - V);

					float NdotL = max(dot(N, L), 0.0);

					if(NdotL > 0.0) {
						// Sample environment at fixed mip level
						// VNDF importance sampling handles the distribution filtering
						vec3 sampleColor = bilinearCubeUV(envMap, L, mipInt);

						// Weight by NdotL for the split-sum approximation
						// VNDF PDF naturally accounts for the visible microfacet distribution
						prefilteredColor += sampleColor * NdotL;
						totalWeight += NdotL;
					}
				}

				if (totalWeight > 0.0) {
					prefilteredColor = prefilteredColor / totalWeight;
				}

				gl_FragColor = vec4(prefilteredColor, 1.0);
			}
		`,blending:qi,depthTest:!1,depthWrite:!1})}function gy(s,e,n){const r=new Float32Array(Qr),o=new ne(0,1,0);return new Di({name:"SphericalGaussianBlur",defines:{n:Qr,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/n,CUBEUV_MAX_MIP:`${s}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:r},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:o}},vertexShader:Vl(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:qi,depthTest:!1,depthWrite:!1})}function gm(){return new Di({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Vl(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:qi,depthTest:!1,depthWrite:!1})}function _m(){return new Di({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Vl(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:qi,depthTest:!1,depthWrite:!1})}function Vl(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}class hg extends bi{constructor(e=1,n={}){super(e,e,n),this.isWebGLCubeRenderTarget=!0;const r={width:e,height:e,depth:1},o=[r,r,r,r,r,r];this.texture=new og(o),this._setTextureOptions(n),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,n){this.texture.type=n.type,this.texture.colorSpace=n.colorSpace,this.texture.generateMipmaps=n.generateMipmaps,this.texture.minFilter=n.minFilter,this.texture.magFilter=n.magFilter;const r={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},o=new ja(5,5,5),u=new Di({name:"CubemapFromEquirect",uniforms:js(r.uniforms),vertexShader:r.vertexShader,fragmentShader:r.fragmentShader,side:In,blending:qi});u.uniforms.tEquirect.value=n;const c=new ii(o,u),d=n.minFilter;return n.minFilter===Jr&&(n.minFilter=_n),new Ev(1,10,this).update(e,c),n.minFilter=d,c.geometry.dispose(),c.material.dispose(),this}clear(e,n=!0,r=!0,o=!0){const u=e.getRenderTarget();for(let c=0;c<6;c++)e.setRenderTarget(this,c),e.clear(n,r,o);e.setRenderTarget(u)}}function _y(s){let e=new WeakMap,n=new WeakMap,r=null;function o(g,y=!1){return g==null?null:y?c(g):u(g)}function u(g){if(g&&g.isTexture){const y=g.mapping;if(y===Ac||y===Cc)if(e.has(g)){const M=e.get(g).texture;return d(M,g.mapping)}else{const M=g.image;if(M&&M.height>0){const C=new hg(M.height);return C.fromEquirectangularTexture(s,g),e.set(g,C),g.addEventListener("dispose",m),d(C.texture,g.mapping)}else return null}}return g}function c(g){if(g&&g.isTexture){const y=g.mapping,M=y===Ac||y===Cc,C=y===ts||y===Gs;if(M||C){let _=n.get(g);const v=_!==void 0?_.texture.pmremVersion:0;if(g.isRenderTargetTexture&&g.pmremVersion!==v)return r===null&&(r=new pm(s)),_=M?r.fromEquirectangular(g,_):r.fromCubemap(g,_),_.texture.pmremVersion=g.pmremVersion,n.set(g,_),_.texture;if(_!==void 0)return _.texture;{const R=g.image;return M&&R&&R.height>0||C&&R&&p(R)?(r===null&&(r=new pm(s)),_=M?r.fromEquirectangular(g):r.fromCubemap(g),_.texture.pmremVersion=g.pmremVersion,n.set(g,_),g.addEventListener("dispose",x),_.texture):null}}}return g}function d(g,y){return y===Ac?g.mapping=ts:y===Cc&&(g.mapping=Gs),g}function p(g){let y=0;const M=6;for(let C=0;C<M;C++)g[C]!==void 0&&y++;return y===M}function m(g){const y=g.target;y.removeEventListener("dispose",m);const M=e.get(y);M!==void 0&&(e.delete(y),M.dispose())}function x(g){const y=g.target;y.removeEventListener("dispose",x);const M=n.get(y);M!==void 0&&(n.delete(y),M.dispose())}function S(){e=new WeakMap,n=new WeakMap,r!==null&&(r.dispose(),r=null)}return{get:o,dispose:S}}function vy(s){const e={};function n(r){if(e[r]!==void 0)return e[r];const o=s.getExtension(r);return e[r]=o,o}return{has:function(r){return n(r)!==null},init:function(){n("EXT_color_buffer_float"),n("WEBGL_clip_cull_distance"),n("OES_texture_float_linear"),n("EXT_color_buffer_half_float"),n("WEBGL_multisampled_render_to_texture"),n("WEBGL_render_shared_exponent")},get:function(r){const o=n(r);return o===null&&Fl("WebGLRenderer: "+r+" extension not supported."),o}}}function xy(s,e,n,r){const o={},u=new WeakMap;function c(S){const g=S.target;g.index!==null&&e.remove(g.index);for(const M in g.attributes)e.remove(g.attributes[M]);g.removeEventListener("dispose",c),delete o[g.id];const y=u.get(g);y&&(e.remove(y),u.delete(g)),r.releaseStatesOfGeometry(g),g.isInstancedBufferGeometry===!0&&delete g._maxInstanceCount,n.memory.geometries--}function d(S,g){return o[g.id]===!0||(g.addEventListener("dispose",c),o[g.id]=!0,n.memory.geometries++),g}function p(S){const g=S.attributes;for(const y in g)e.update(g[y],s.ARRAY_BUFFER)}function m(S){const g=[],y=S.index,M=S.attributes.position;let C=0;if(M===void 0)return;if(y!==null){const R=y.array;C=y.version;for(let L=0,b=R.length;L<b;L+=3){const F=R[L+0],U=R[L+1],z=R[L+2];g.push(F,U,U,z,z,F)}}else{const R=M.array;C=M.version;for(let L=0,b=R.length/3-1;L<b;L+=3){const F=L+0,U=L+1,z=L+2;g.push(F,U,U,z,z,F)}}const _=new(M.count>=65535?ig:ng)(g,1);_.version=C;const v=u.get(S);v&&e.remove(v),u.set(S,_)}function x(S){const g=u.get(S);if(g){const y=S.index;y!==null&&g.version<y.version&&m(S)}else m(S);return u.get(S)}return{get:d,update:p,getWireframeAttribute:x}}function Sy(s,e,n){let r;function o(g){r=g}let u,c;function d(g){u=g.type,c=g.bytesPerElement}function p(g,y){s.drawElements(r,y,u,g*c),n.update(y,r,1)}function m(g,y,M){M!==0&&(s.drawElementsInstanced(r,y,u,g*c,M),n.update(y,r,M))}function x(g,y,M){if(M===0)return;e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(r,y,0,u,g,0,M);let _=0;for(let v=0;v<M;v++)_+=y[v];n.update(_,r,1)}function S(g,y,M,C){if(M===0)return;const _=e.get("WEBGL_multi_draw");if(_===null)for(let v=0;v<g.length;v++)m(g[v]/c,y[v],C[v]);else{_.multiDrawElementsInstancedWEBGL(r,y,0,u,g,0,C,0,M);let v=0;for(let R=0;R<M;R++)v+=y[R]*C[R];n.update(v,r,1)}}this.setMode=o,this.setIndex=d,this.render=p,this.renderInstances=m,this.renderMultiDraw=x,this.renderMultiDrawInstances=S}function yy(s){const e={geometries:0,textures:0},n={frame:0,calls:0,triangles:0,points:0,lines:0};function r(u,c,d){switch(n.calls++,c){case s.TRIANGLES:n.triangles+=d*(u/3);break;case s.LINES:n.lines+=d*(u/2);break;case s.LINE_STRIP:n.lines+=d*(u-1);break;case s.LINE_LOOP:n.lines+=d*u;break;case s.POINTS:n.points+=d*u;break;default:wt("WebGLInfo: Unknown draw mode:",c);break}}function o(){n.calls=0,n.triangles=0,n.points=0,n.lines=0}return{memory:e,render:n,programs:null,autoReset:!0,reset:o,update:r}}function My(s,e,n){const r=new WeakMap,o=new qt;function u(c,d,p){const m=c.morphTargetInfluences,x=d.morphAttributes.position||d.morphAttributes.normal||d.morphAttributes.color,S=x!==void 0?x.length:0;let g=r.get(d);if(g===void 0||g.count!==S){let fe=function(){A.dispose(),r.delete(d),d.removeEventListener("dispose",fe)};var y=fe;g!==void 0&&g.texture.dispose();const M=d.morphAttributes.position!==void 0,C=d.morphAttributes.normal!==void 0,_=d.morphAttributes.color!==void 0,v=d.morphAttributes.position||[],R=d.morphAttributes.normal||[],L=d.morphAttributes.color||[];let b=0;M===!0&&(b=1),C===!0&&(b=2),_===!0&&(b=3);let F=d.attributes.position.count*b,U=1;F>e.maxTextureSize&&(U=Math.ceil(F/e.maxTextureSize),F=e.maxTextureSize);const z=new Float32Array(F*U*4*S),A=new Jm(z,F,U,S);A.type=Ai,A.needsUpdate=!0;const D=b*4;for(let O=0;O<S;O++){const te=v[O],Q=R[O],oe=L[O],K=F*U*4*O;for(let ee=0;ee<te.count;ee++){const W=ee*D;M===!0&&(o.fromBufferAttribute(te,ee),z[K+W+0]=o.x,z[K+W+1]=o.y,z[K+W+2]=o.z,z[K+W+3]=0),C===!0&&(o.fromBufferAttribute(Q,ee),z[K+W+4]=o.x,z[K+W+5]=o.y,z[K+W+6]=o.z,z[K+W+7]=0),_===!0&&(o.fromBufferAttribute(oe,ee),z[K+W+8]=o.x,z[K+W+9]=o.y,z[K+W+10]=o.z,z[K+W+11]=oe.itemSize===4?o.w:1)}}g={count:S,texture:A,size:new Lt(F,U)},r.set(d,g),d.addEventListener("dispose",fe)}if(c.isInstancedMesh===!0&&c.morphTexture!==null)p.getUniforms().setValue(s,"morphTexture",c.morphTexture,n);else{let M=0;for(let _=0;_<m.length;_++)M+=m[_];const C=d.morphTargetsRelative?1:1-M;p.getUniforms().setValue(s,"morphTargetBaseInfluence",C),p.getUniforms().setValue(s,"morphTargetInfluences",m)}p.getUniforms().setValue(s,"morphTargetsTexture",g.texture,n),p.getUniforms().setValue(s,"morphTargetsTextureSize",g.size)}return{update:u}}function Ey(s,e,n,r,o){let u=new WeakMap;function c(m){const x=o.render.frame,S=m.geometry,g=e.get(m,S);if(u.get(g)!==x&&(e.update(g),u.set(g,x)),m.isInstancedMesh&&(m.hasEventListener("dispose",p)===!1&&m.addEventListener("dispose",p),u.get(m)!==x&&(n.update(m.instanceMatrix,s.ARRAY_BUFFER),m.instanceColor!==null&&n.update(m.instanceColor,s.ARRAY_BUFFER),u.set(m,x))),m.isSkinnedMesh){const y=m.skeleton;u.get(y)!==x&&(y.update(),u.set(y,x))}return g}function d(){u=new WeakMap}function p(m){const x=m.target;x.removeEventListener("dispose",p),r.releaseStatesOfObject(x),n.remove(x.instanceMatrix),x.instanceColor!==null&&n.remove(x.instanceColor)}return{update:c,dispose:d}}const Ty={[Om]:"LINEAR_TONE_MAPPING",[Bm]:"REINHARD_TONE_MAPPING",[km]:"CINEON_TONE_MAPPING",[zm]:"ACES_FILMIC_TONE_MAPPING",[Hm]:"AGX_TONE_MAPPING",[Gm]:"NEUTRAL_TONE_MAPPING",[Vm]:"CUSTOM_TONE_MAPPING"};function wy(s,e,n,r,o){const u=new bi(e,n,{type:s,depthBuffer:r,stencilBuffer:o}),c=new bi(e,n,{type:Ki,depthBuffer:!1,stencilBuffer:!1}),d=new Gn;d.setAttribute("position",new Tn([-1,3,0,-1,-1,0,3,-1,0],3)),d.setAttribute("uv",new Tn([0,2,0,0,2,0],2));const p=new Sv({uniforms:{tDiffuse:{value:null}},vertexShader:`
			precision highp float;

			uniform mat4 modelViewMatrix;
			uniform mat4 projectionMatrix;

			attribute vec3 position;
			attribute vec2 uv;

			varying vec2 vUv;

			void main() {
				vUv = uv;
				gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			}`,fragmentShader:`
			precision highp float;

			uniform sampler2D tDiffuse;

			varying vec2 vUv;

			#include <tonemapping_pars_fragment>
			#include <colorspace_pars_fragment>

			void main() {
				gl_FragColor = texture2D( tDiffuse, vUv );

				#ifdef LINEAR_TONE_MAPPING
					gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );
				#elif defined( REINHARD_TONE_MAPPING )
					gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );
				#elif defined( CINEON_TONE_MAPPING )
					gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );
				#elif defined( ACES_FILMIC_TONE_MAPPING )
					gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );
				#elif defined( AGX_TONE_MAPPING )
					gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );
				#elif defined( NEUTRAL_TONE_MAPPING )
					gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );
				#elif defined( CUSTOM_TONE_MAPPING )
					gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );
				#endif

				#ifdef SRGB_TRANSFER
					gl_FragColor = sRGBTransferOETF( gl_FragColor );
				#endif
			}`,depthTest:!1,depthWrite:!1}),m=new ii(d,p),x=new fg(-1,1,1,-1,0,1);let S=null,g=null,y=!1,M,C=null,_=[],v=!1;this.setSize=function(R,L){u.setSize(R,L),c.setSize(R,L);for(let b=0;b<_.length;b++){const F=_[b];F.setSize&&F.setSize(R,L)}},this.setEffects=function(R){_=R,v=_.length>0&&_[0].isRenderPass===!0;const L=u.width,b=u.height;for(let F=0;F<_.length;F++){const U=_[F];U.setSize&&U.setSize(L,b)}},this.begin=function(R,L){if(y||R.toneMapping===Ri&&_.length===0)return!1;if(C=L,L!==null){const b=L.width,F=L.height;(u.width!==b||u.height!==F)&&this.setSize(b,F)}return v===!1&&R.setRenderTarget(u),M=R.toneMapping,R.toneMapping=Ri,!0},this.hasRenderPass=function(){return v},this.end=function(R,L){R.toneMapping=M,y=!0;let b=u,F=c;for(let U=0;U<_.length;U++){const z=_[U];if(z.enabled!==!1&&(z.render(R,F,b,L),z.needsSwap!==!1)){const A=b;b=F,F=A}}if(S!==R.outputColorSpace||g!==R.toneMapping){S=R.outputColorSpace,g=R.toneMapping,p.defines={},Et.getTransfer(S)===Dt&&(p.defines.SRGB_TRANSFER="");const U=Ty[g];U&&(p.defines[U]=""),p.needsUpdate=!0}p.uniforms.tDiffuse.value=b.texture,R.setRenderTarget(C),R.render(m,x),C=null,y=!1},this.isCompositing=function(){return y},this.dispose=function(){u.dispose(),c.dispose(),d.dispose(),p.dispose()}}const pg=new En,Zf=new Ha(1,1),mg=new Jm,gg=new K0,_g=new og,vm=[],xm=[],Sm=new Float32Array(16),ym=new Float32Array(9),Mm=new Float32Array(4);function $s(s,e,n){const r=s[0];if(r<=0||r>0)return s;const o=e*n;let u=vm[o];if(u===void 0&&(u=new Float32Array(o),vm[o]=u),e!==0){r.toArray(u,0);for(let c=1,d=0;c!==e;++c)d+=n,s[c].toArray(u,d)}return u}function tn(s,e){if(s.length!==e.length)return!1;for(let n=0,r=s.length;n<r;n++)if(s[n]!==e[n])return!1;return!0}function nn(s,e){for(let n=0,r=e.length;n<r;n++)s[n]=e[n]}function Hl(s,e){let n=xm[e];n===void 0&&(n=new Int32Array(e),xm[e]=n);for(let r=0;r!==e;++r)n[r]=s.allocateTextureUnit();return n}function Ay(s,e){const n=this.cache;n[0]!==e&&(s.uniform1f(this.addr,e),n[0]=e)}function Cy(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y)&&(s.uniform2f(this.addr,e.x,e.y),n[0]=e.x,n[1]=e.y);else{if(tn(n,e))return;s.uniform2fv(this.addr,e),nn(n,e)}}function Ry(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z)&&(s.uniform3f(this.addr,e.x,e.y,e.z),n[0]=e.x,n[1]=e.y,n[2]=e.z);else if(e.r!==void 0)(n[0]!==e.r||n[1]!==e.g||n[2]!==e.b)&&(s.uniform3f(this.addr,e.r,e.g,e.b),n[0]=e.r,n[1]=e.g,n[2]=e.b);else{if(tn(n,e))return;s.uniform3fv(this.addr,e),nn(n,e)}}function by(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z||n[3]!==e.w)&&(s.uniform4f(this.addr,e.x,e.y,e.z,e.w),n[0]=e.x,n[1]=e.y,n[2]=e.z,n[3]=e.w);else{if(tn(n,e))return;s.uniform4fv(this.addr,e),nn(n,e)}}function Py(s,e){const n=this.cache,r=e.elements;if(r===void 0){if(tn(n,e))return;s.uniformMatrix2fv(this.addr,!1,e),nn(n,e)}else{if(tn(n,r))return;Mm.set(r),s.uniformMatrix2fv(this.addr,!1,Mm),nn(n,r)}}function Dy(s,e){const n=this.cache,r=e.elements;if(r===void 0){if(tn(n,e))return;s.uniformMatrix3fv(this.addr,!1,e),nn(n,e)}else{if(tn(n,r))return;ym.set(r),s.uniformMatrix3fv(this.addr,!1,ym),nn(n,r)}}function Ly(s,e){const n=this.cache,r=e.elements;if(r===void 0){if(tn(n,e))return;s.uniformMatrix4fv(this.addr,!1,e),nn(n,e)}else{if(tn(n,r))return;Sm.set(r),s.uniformMatrix4fv(this.addr,!1,Sm),nn(n,r)}}function Ny(s,e){const n=this.cache;n[0]!==e&&(s.uniform1i(this.addr,e),n[0]=e)}function Iy(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y)&&(s.uniform2i(this.addr,e.x,e.y),n[0]=e.x,n[1]=e.y);else{if(tn(n,e))return;s.uniform2iv(this.addr,e),nn(n,e)}}function Uy(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z)&&(s.uniform3i(this.addr,e.x,e.y,e.z),n[0]=e.x,n[1]=e.y,n[2]=e.z);else{if(tn(n,e))return;s.uniform3iv(this.addr,e),nn(n,e)}}function Fy(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z||n[3]!==e.w)&&(s.uniform4i(this.addr,e.x,e.y,e.z,e.w),n[0]=e.x,n[1]=e.y,n[2]=e.z,n[3]=e.w);else{if(tn(n,e))return;s.uniform4iv(this.addr,e),nn(n,e)}}function Oy(s,e){const n=this.cache;n[0]!==e&&(s.uniform1ui(this.addr,e),n[0]=e)}function By(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y)&&(s.uniform2ui(this.addr,e.x,e.y),n[0]=e.x,n[1]=e.y);else{if(tn(n,e))return;s.uniform2uiv(this.addr,e),nn(n,e)}}function ky(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z)&&(s.uniform3ui(this.addr,e.x,e.y,e.z),n[0]=e.x,n[1]=e.y,n[2]=e.z);else{if(tn(n,e))return;s.uniform3uiv(this.addr,e),nn(n,e)}}function zy(s,e){const n=this.cache;if(e.x!==void 0)(n[0]!==e.x||n[1]!==e.y||n[2]!==e.z||n[3]!==e.w)&&(s.uniform4ui(this.addr,e.x,e.y,e.z,e.w),n[0]=e.x,n[1]=e.y,n[2]=e.z,n[3]=e.w);else{if(tn(n,e))return;s.uniform4uiv(this.addr,e),nn(n,e)}}function Vy(s,e,n){const r=this.cache,o=n.allocateTextureUnit();r[0]!==o&&(s.uniform1i(this.addr,o),r[0]=o);let u;this.type===s.SAMPLER_2D_SHADOW?(Zf.compareFunction=n.isReversedDepthBuffer()?ld:od,u=Zf):u=pg,n.setTexture2D(e||u,o)}function Hy(s,e,n){const r=this.cache,o=n.allocateTextureUnit();r[0]!==o&&(s.uniform1i(this.addr,o),r[0]=o),n.setTexture3D(e||gg,o)}function Gy(s,e,n){const r=this.cache,o=n.allocateTextureUnit();r[0]!==o&&(s.uniform1i(this.addr,o),r[0]=o),n.setTextureCube(e||_g,o)}function Wy(s,e,n){const r=this.cache,o=n.allocateTextureUnit();r[0]!==o&&(s.uniform1i(this.addr,o),r[0]=o),n.setTexture2DArray(e||mg,o)}function Xy(s){switch(s){case 5126:return Ay;case 35664:return Cy;case 35665:return Ry;case 35666:return by;case 35674:return Py;case 35675:return Dy;case 35676:return Ly;case 5124:case 35670:return Ny;case 35667:case 35671:return Iy;case 35668:case 35672:return Uy;case 35669:case 35673:return Fy;case 5125:return Oy;case 36294:return By;case 36295:return ky;case 36296:return zy;case 35678:case 36198:case 36298:case 36306:case 35682:return Vy;case 35679:case 36299:case 36307:return Hy;case 35680:case 36300:case 36308:case 36293:return Gy;case 36289:case 36303:case 36311:case 36292:return Wy}}function jy(s,e){s.uniform1fv(this.addr,e)}function Yy(s,e){const n=$s(e,this.size,2);s.uniform2fv(this.addr,n)}function qy(s,e){const n=$s(e,this.size,3);s.uniform3fv(this.addr,n)}function $y(s,e){const n=$s(e,this.size,4);s.uniform4fv(this.addr,n)}function Ky(s,e){const n=$s(e,this.size,4);s.uniformMatrix2fv(this.addr,!1,n)}function Zy(s,e){const n=$s(e,this.size,9);s.uniformMatrix3fv(this.addr,!1,n)}function Qy(s,e){const n=$s(e,this.size,16);s.uniformMatrix4fv(this.addr,!1,n)}function Jy(s,e){s.uniform1iv(this.addr,e)}function eM(s,e){s.uniform2iv(this.addr,e)}function tM(s,e){s.uniform3iv(this.addr,e)}function nM(s,e){s.uniform4iv(this.addr,e)}function iM(s,e){s.uniform1uiv(this.addr,e)}function rM(s,e){s.uniform2uiv(this.addr,e)}function sM(s,e){s.uniform3uiv(this.addr,e)}function aM(s,e){s.uniform4uiv(this.addr,e)}function oM(s,e,n){const r=this.cache,o=e.length,u=Hl(n,o);tn(r,u)||(s.uniform1iv(this.addr,u),nn(r,u));let c;this.type===s.SAMPLER_2D_SHADOW?c=Zf:c=pg;for(let d=0;d!==o;++d)n.setTexture2D(e[d]||c,u[d])}function lM(s,e,n){const r=this.cache,o=e.length,u=Hl(n,o);tn(r,u)||(s.uniform1iv(this.addr,u),nn(r,u));for(let c=0;c!==o;++c)n.setTexture3D(e[c]||gg,u[c])}function uM(s,e,n){const r=this.cache,o=e.length,u=Hl(n,o);tn(r,u)||(s.uniform1iv(this.addr,u),nn(r,u));for(let c=0;c!==o;++c)n.setTextureCube(e[c]||_g,u[c])}function cM(s,e,n){const r=this.cache,o=e.length,u=Hl(n,o);tn(r,u)||(s.uniform1iv(this.addr,u),nn(r,u));for(let c=0;c!==o;++c)n.setTexture2DArray(e[c]||mg,u[c])}function fM(s){switch(s){case 5126:return jy;case 35664:return Yy;case 35665:return qy;case 35666:return $y;case 35674:return Ky;case 35675:return Zy;case 35676:return Qy;case 5124:case 35670:return Jy;case 35667:case 35671:return eM;case 35668:case 35672:return tM;case 35669:case 35673:return nM;case 5125:return iM;case 36294:return rM;case 36295:return sM;case 36296:return aM;case 35678:case 36198:case 36298:case 36306:case 35682:return oM;case 35679:case 36299:case 36307:return lM;case 35680:case 36300:case 36308:case 36293:return uM;case 36289:case 36303:case 36311:case 36292:return cM}}class dM{constructor(e,n,r){this.id=e,this.addr=r,this.cache=[],this.type=n.type,this.setValue=Xy(n.type)}}class hM{constructor(e,n,r){this.id=e,this.addr=r,this.cache=[],this.type=n.type,this.size=n.size,this.setValue=fM(n.type)}}class pM{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,n,r){const o=this.seq;for(let u=0,c=o.length;u!==c;++u){const d=o[u];d.setValue(e,n[d.id],r)}}}const rf=/(\w+)(\])?(\[|\.)?/g;function Em(s,e){s.seq.push(e),s.map[e.id]=e}function mM(s,e,n){const r=s.name,o=r.length;for(rf.lastIndex=0;;){const u=rf.exec(r),c=rf.lastIndex;let d=u[1];const p=u[2]==="]",m=u[3];if(p&&(d=d|0),m===void 0||m==="["&&c+2===o){Em(n,m===void 0?new dM(d,s,e):new hM(d,s,e));break}else{let S=n.map[d];S===void 0&&(S=new pM(d),Em(n,S)),n=S}}}class Ll{constructor(e,n){this.seq=[],this.map={};const r=e.getProgramParameter(n,e.ACTIVE_UNIFORMS);for(let c=0;c<r;++c){const d=e.getActiveUniform(n,c),p=e.getUniformLocation(n,d.name);mM(d,p,this)}const o=[],u=[];for(const c of this.seq)c.type===e.SAMPLER_2D_SHADOW||c.type===e.SAMPLER_CUBE_SHADOW||c.type===e.SAMPLER_2D_ARRAY_SHADOW?o.push(c):u.push(c);o.length>0&&(this.seq=o.concat(u))}setValue(e,n,r,o){const u=this.map[n];u!==void 0&&u.setValue(e,r,o)}setOptional(e,n,r){const o=n[r];o!==void 0&&this.setValue(e,r,o)}static upload(e,n,r,o){for(let u=0,c=n.length;u!==c;++u){const d=n[u],p=r[d.id];p.needsUpdate!==!1&&d.setValue(e,p.value,o)}}static seqWithValue(e,n){const r=[];for(let o=0,u=e.length;o!==u;++o){const c=e[o];c.id in n&&r.push(c)}return r}}function Tm(s,e,n){const r=s.createShader(e);return s.shaderSource(r,n),s.compileShader(r),r}const gM=37297;let _M=0;function vM(s,e){const n=s.split(`
`),r=[],o=Math.max(e-6,0),u=Math.min(e+6,n.length);for(let c=o;c<u;c++){const d=c+1;r.push(`${d===e?">":" "} ${d}: ${n[c]}`)}return r.join(`
`)}const wm=new ft;function xM(s){Et._getMatrix(wm,Et.workingColorSpace,s);const e=`mat3( ${wm.elements.map(n=>n.toFixed(4))} )`;switch(Et.getTransfer(s)){case Nl:return[e,"LinearTransferOETF"];case Dt:return[e,"sRGBTransferOETF"];default:return ot("WebGLProgram: Unsupported color space: ",s),[e,"LinearTransferOETF"]}}function Am(s,e,n){const r=s.getShaderParameter(e,s.COMPILE_STATUS),u=(s.getShaderInfoLog(e)||"").trim();if(r&&u==="")return"";const c=/ERROR: 0:(\d+)/.exec(u);if(c){const d=parseInt(c[1]);return n.toUpperCase()+`

`+u+`

`+vM(s.getShaderSource(e),d)}else return u}function SM(s,e){const n=xM(e);return[`vec4 ${s}( vec4 value ) {`,`	return ${n[1]}( vec4( value.rgb * ${n[0]}, value.a ) );`,"}"].join(`
`)}const yM={[Om]:"Linear",[Bm]:"Reinhard",[km]:"Cineon",[zm]:"ACESFilmic",[Hm]:"AgX",[Gm]:"Neutral",[Vm]:"Custom"};function MM(s,e){const n=yM[e];return n===void 0?(ot("WebGLProgram: Unsupported toneMapping:",e),"vec3 "+s+"( vec3 color ) { return LinearToneMapping( color ); }"):"vec3 "+s+"( vec3 color ) { return "+n+"ToneMapping( color ); }"}const Al=new ne;function EM(){Et.getLuminanceCoefficients(Al);const s=Al.x.toFixed(4),e=Al.y.toFixed(4),n=Al.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${s}, ${e}, ${n} );`,"	return dot( weights, rgb );","}"].join(`
`)}function TM(s){return[s.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",s.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Ba).join(`
`)}function wM(s){const e=[];for(const n in s){const r=s[n];r!==!1&&e.push("#define "+n+" "+r)}return e.join(`
`)}function AM(s,e){const n={},r=s.getProgramParameter(e,s.ACTIVE_ATTRIBUTES);for(let o=0;o<r;o++){const u=s.getActiveAttrib(e,o),c=u.name;let d=1;u.type===s.FLOAT_MAT2&&(d=2),u.type===s.FLOAT_MAT3&&(d=3),u.type===s.FLOAT_MAT4&&(d=4),n[c]={type:u.type,location:s.getAttribLocation(e,c),locationSize:d}}return n}function Ba(s){return s!==""}function Cm(s,e){const n=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return s.replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,n).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function Rm(s,e){return s.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}const CM=/^[ \t]*#include +<([\w\d./]+)>/gm;function Qf(s){return s.replace(CM,bM)}const RM=new Map;function bM(s,e){let n=dt[e];if(n===void 0){const r=RM.get(e);if(r!==void 0)n=dt[r],ot('WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,r);else throw new Error("Can not resolve #include <"+e+">")}return Qf(n)}const PM=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function bm(s){return s.replace(PM,DM)}function DM(s,e,n,r){let o="";for(let u=parseInt(e);u<parseInt(n);u++)o+=r.replace(/\[\s*i\s*\]/g,"[ "+u+" ]").replace(/UNROLLED_LOOP_INDEX/g,u);return o}function Pm(s){let e=`precision ${s.precision} float;
	precision ${s.precision} int;
	precision ${s.precision} sampler2D;
	precision ${s.precision} samplerCube;
	precision ${s.precision} sampler3D;
	precision ${s.precision} sampler2DArray;
	precision ${s.precision} sampler2DShadow;
	precision ${s.precision} samplerCubeShadow;
	precision ${s.precision} sampler2DArrayShadow;
	precision ${s.precision} isampler2D;
	precision ${s.precision} isampler3D;
	precision ${s.precision} isamplerCube;
	precision ${s.precision} isampler2DArray;
	precision ${s.precision} usampler2D;
	precision ${s.precision} usampler3D;
	precision ${s.precision} usamplerCube;
	precision ${s.precision} usampler2DArray;
	`;return s.precision==="highp"?e+=`
#define HIGH_PRECISION`:s.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:s.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}const LM={[Cl]:"SHADOWMAP_TYPE_PCF",[Oa]:"SHADOWMAP_TYPE_VSM"};function NM(s){return LM[s.shadowMapType]||"SHADOWMAP_TYPE_BASIC"}const IM={[ts]:"ENVMAP_TYPE_CUBE",[Gs]:"ENVMAP_TYPE_CUBE",[Bl]:"ENVMAP_TYPE_CUBE_UV"};function UM(s){return s.envMap===!1?"ENVMAP_TYPE_CUBE":IM[s.envMapMode]||"ENVMAP_TYPE_CUBE"}const FM={[Gs]:"ENVMAP_MODE_REFRACTION"};function OM(s){return s.envMap===!1?"ENVMAP_MODE_REFLECTION":FM[s.envMapMode]||"ENVMAP_MODE_REFLECTION"}const BM={[Fm]:"ENVMAP_BLENDING_MULTIPLY",[R0]:"ENVMAP_BLENDING_MIX",[b0]:"ENVMAP_BLENDING_ADD"};function kM(s){return s.envMap===!1?"ENVMAP_BLENDING_NONE":BM[s.combine]||"ENVMAP_BLENDING_NONE"}function zM(s){const e=s.envMapCubeUVHeight;if(e===null)return null;const n=Math.log2(e)-2,r=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,n),112)),texelHeight:r,maxMip:n}}function VM(s,e,n,r){const o=s.getContext(),u=n.defines;let c=n.vertexShader,d=n.fragmentShader;const p=NM(n),m=UM(n),x=OM(n),S=kM(n),g=zM(n),y=TM(n),M=wM(u),C=o.createProgram();let _,v,R=n.glslVersion?"#version "+n.glslVersion+`
`:"";n.isRawShaderMaterial?(_=["#define SHADER_TYPE "+n.shaderType,"#define SHADER_NAME "+n.shaderName,M].filter(Ba).join(`
`),_.length>0&&(_+=`
`),v=["#define SHADER_TYPE "+n.shaderType,"#define SHADER_NAME "+n.shaderName,M].filter(Ba).join(`
`),v.length>0&&(v+=`
`)):(_=[Pm(n),"#define SHADER_TYPE "+n.shaderType,"#define SHADER_NAME "+n.shaderName,M,n.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",n.batching?"#define USE_BATCHING":"",n.batchingColor?"#define USE_BATCHING_COLOR":"",n.instancing?"#define USE_INSTANCING":"",n.instancingColor?"#define USE_INSTANCING_COLOR":"",n.instancingMorph?"#define USE_INSTANCING_MORPH":"",n.useFog&&n.fog?"#define USE_FOG":"",n.useFog&&n.fogExp2?"#define FOG_EXP2":"",n.map?"#define USE_MAP":"",n.envMap?"#define USE_ENVMAP":"",n.envMap?"#define "+x:"",n.lightMap?"#define USE_LIGHTMAP":"",n.aoMap?"#define USE_AOMAP":"",n.bumpMap?"#define USE_BUMPMAP":"",n.normalMap?"#define USE_NORMALMAP":"",n.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",n.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",n.displacementMap?"#define USE_DISPLACEMENTMAP":"",n.emissiveMap?"#define USE_EMISSIVEMAP":"",n.anisotropy?"#define USE_ANISOTROPY":"",n.anisotropyMap?"#define USE_ANISOTROPYMAP":"",n.clearcoatMap?"#define USE_CLEARCOATMAP":"",n.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",n.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",n.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",n.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",n.specularMap?"#define USE_SPECULARMAP":"",n.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",n.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",n.roughnessMap?"#define USE_ROUGHNESSMAP":"",n.metalnessMap?"#define USE_METALNESSMAP":"",n.alphaMap?"#define USE_ALPHAMAP":"",n.alphaHash?"#define USE_ALPHAHASH":"",n.transmission?"#define USE_TRANSMISSION":"",n.transmissionMap?"#define USE_TRANSMISSIONMAP":"",n.thicknessMap?"#define USE_THICKNESSMAP":"",n.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",n.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",n.mapUv?"#define MAP_UV "+n.mapUv:"",n.alphaMapUv?"#define ALPHAMAP_UV "+n.alphaMapUv:"",n.lightMapUv?"#define LIGHTMAP_UV "+n.lightMapUv:"",n.aoMapUv?"#define AOMAP_UV "+n.aoMapUv:"",n.emissiveMapUv?"#define EMISSIVEMAP_UV "+n.emissiveMapUv:"",n.bumpMapUv?"#define BUMPMAP_UV "+n.bumpMapUv:"",n.normalMapUv?"#define NORMALMAP_UV "+n.normalMapUv:"",n.displacementMapUv?"#define DISPLACEMENTMAP_UV "+n.displacementMapUv:"",n.metalnessMapUv?"#define METALNESSMAP_UV "+n.metalnessMapUv:"",n.roughnessMapUv?"#define ROUGHNESSMAP_UV "+n.roughnessMapUv:"",n.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+n.anisotropyMapUv:"",n.clearcoatMapUv?"#define CLEARCOATMAP_UV "+n.clearcoatMapUv:"",n.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+n.clearcoatNormalMapUv:"",n.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+n.clearcoatRoughnessMapUv:"",n.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+n.iridescenceMapUv:"",n.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+n.iridescenceThicknessMapUv:"",n.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+n.sheenColorMapUv:"",n.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+n.sheenRoughnessMapUv:"",n.specularMapUv?"#define SPECULARMAP_UV "+n.specularMapUv:"",n.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+n.specularColorMapUv:"",n.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+n.specularIntensityMapUv:"",n.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+n.transmissionMapUv:"",n.thicknessMapUv?"#define THICKNESSMAP_UV "+n.thicknessMapUv:"",n.vertexTangents&&n.flatShading===!1?"#define USE_TANGENT":"",n.vertexColors?"#define USE_COLOR":"",n.vertexAlphas?"#define USE_COLOR_ALPHA":"",n.vertexUv1s?"#define USE_UV1":"",n.vertexUv2s?"#define USE_UV2":"",n.vertexUv3s?"#define USE_UV3":"",n.pointsUvs?"#define USE_POINTS_UV":"",n.flatShading?"#define FLAT_SHADED":"",n.skinning?"#define USE_SKINNING":"",n.morphTargets?"#define USE_MORPHTARGETS":"",n.morphNormals&&n.flatShading===!1?"#define USE_MORPHNORMALS":"",n.morphColors?"#define USE_MORPHCOLORS":"",n.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+n.morphTextureStride:"",n.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+n.morphTargetsCount:"",n.doubleSided?"#define DOUBLE_SIDED":"",n.flipSided?"#define FLIP_SIDED":"",n.shadowMapEnabled?"#define USE_SHADOWMAP":"",n.shadowMapEnabled?"#define "+p:"",n.sizeAttenuation?"#define USE_SIZEATTENUATION":"",n.numLightProbes>0?"#define USE_LIGHT_PROBES":"",n.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",n.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Ba).join(`
`),v=[Pm(n),"#define SHADER_TYPE "+n.shaderType,"#define SHADER_NAME "+n.shaderName,M,n.useFog&&n.fog?"#define USE_FOG":"",n.useFog&&n.fogExp2?"#define FOG_EXP2":"",n.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",n.map?"#define USE_MAP":"",n.matcap?"#define USE_MATCAP":"",n.envMap?"#define USE_ENVMAP":"",n.envMap?"#define "+m:"",n.envMap?"#define "+x:"",n.envMap?"#define "+S:"",g?"#define CUBEUV_TEXEL_WIDTH "+g.texelWidth:"",g?"#define CUBEUV_TEXEL_HEIGHT "+g.texelHeight:"",g?"#define CUBEUV_MAX_MIP "+g.maxMip+".0":"",n.lightMap?"#define USE_LIGHTMAP":"",n.aoMap?"#define USE_AOMAP":"",n.bumpMap?"#define USE_BUMPMAP":"",n.normalMap?"#define USE_NORMALMAP":"",n.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",n.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",n.emissiveMap?"#define USE_EMISSIVEMAP":"",n.anisotropy?"#define USE_ANISOTROPY":"",n.anisotropyMap?"#define USE_ANISOTROPYMAP":"",n.clearcoat?"#define USE_CLEARCOAT":"",n.clearcoatMap?"#define USE_CLEARCOATMAP":"",n.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",n.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",n.dispersion?"#define USE_DISPERSION":"",n.iridescence?"#define USE_IRIDESCENCE":"",n.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",n.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",n.specularMap?"#define USE_SPECULARMAP":"",n.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",n.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",n.roughnessMap?"#define USE_ROUGHNESSMAP":"",n.metalnessMap?"#define USE_METALNESSMAP":"",n.alphaMap?"#define USE_ALPHAMAP":"",n.alphaTest?"#define USE_ALPHATEST":"",n.alphaHash?"#define USE_ALPHAHASH":"",n.sheen?"#define USE_SHEEN":"",n.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",n.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",n.transmission?"#define USE_TRANSMISSION":"",n.transmissionMap?"#define USE_TRANSMISSIONMAP":"",n.thicknessMap?"#define USE_THICKNESSMAP":"",n.vertexTangents&&n.flatShading===!1?"#define USE_TANGENT":"",n.vertexColors||n.instancingColor?"#define USE_COLOR":"",n.vertexAlphas||n.batchingColor?"#define USE_COLOR_ALPHA":"",n.vertexUv1s?"#define USE_UV1":"",n.vertexUv2s?"#define USE_UV2":"",n.vertexUv3s?"#define USE_UV3":"",n.pointsUvs?"#define USE_POINTS_UV":"",n.gradientMap?"#define USE_GRADIENTMAP":"",n.flatShading?"#define FLAT_SHADED":"",n.doubleSided?"#define DOUBLE_SIDED":"",n.flipSided?"#define FLIP_SIDED":"",n.shadowMapEnabled?"#define USE_SHADOWMAP":"",n.shadowMapEnabled?"#define "+p:"",n.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",n.numLightProbes>0?"#define USE_LIGHT_PROBES":"",n.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",n.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",n.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",n.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",n.toneMapping!==Ri?"#define TONE_MAPPING":"",n.toneMapping!==Ri?dt.tonemapping_pars_fragment:"",n.toneMapping!==Ri?MM("toneMapping",n.toneMapping):"",n.dithering?"#define DITHERING":"",n.opaque?"#define OPAQUE":"",dt.colorspace_pars_fragment,SM("linearToOutputTexel",n.outputColorSpace),EM(),n.useDepthPacking?"#define DEPTH_PACKING "+n.depthPacking:"",`
`].filter(Ba).join(`
`)),c=Qf(c),c=Cm(c,n),c=Rm(c,n),d=Qf(d),d=Cm(d,n),d=Rm(d,n),c=bm(c),d=bm(d),n.isRawShaderMaterial!==!0&&(R=`#version 300 es
`,_=[y,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+_,v=["#define varying in",n.glslVersion===Wp?"":"layout(location = 0) out highp vec4 pc_fragColor;",n.glslVersion===Wp?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+v);const L=R+_+c,b=R+v+d,F=Tm(o,o.VERTEX_SHADER,L),U=Tm(o,o.FRAGMENT_SHADER,b);o.attachShader(C,F),o.attachShader(C,U),n.index0AttributeName!==void 0?o.bindAttribLocation(C,0,n.index0AttributeName):n.morphTargets===!0&&o.bindAttribLocation(C,0,"position"),o.linkProgram(C);function z(O){if(s.debug.checkShaderErrors){const te=o.getProgramInfoLog(C)||"",Q=o.getShaderInfoLog(F)||"",oe=o.getShaderInfoLog(U)||"",K=te.trim(),ee=Q.trim(),W=oe.trim();let q=!0,ae=!0;if(o.getProgramParameter(C,o.LINK_STATUS)===!1)if(q=!1,typeof s.debug.onShaderError=="function")s.debug.onShaderError(o,C,F,U);else{const le=Am(o,F,"vertex"),I=Am(o,U,"fragment");wt("THREE.WebGLProgram: Shader Error "+o.getError()+" - VALIDATE_STATUS "+o.getProgramParameter(C,o.VALIDATE_STATUS)+`

Material Name: `+O.name+`
Material Type: `+O.type+`

Program Info Log: `+K+`
`+le+`
`+I)}else K!==""?ot("WebGLProgram: Program Info Log:",K):(ee===""||W==="")&&(ae=!1);ae&&(O.diagnostics={runnable:q,programLog:K,vertexShader:{log:ee,prefix:_},fragmentShader:{log:W,prefix:v}})}o.deleteShader(F),o.deleteShader(U),A=new Ll(o,C),D=AM(o,C)}let A;this.getUniforms=function(){return A===void 0&&z(this),A};let D;this.getAttributes=function(){return D===void 0&&z(this),D};let fe=n.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return fe===!1&&(fe=o.getProgramParameter(C,gM)),fe},this.destroy=function(){r.releaseStatesOfProgram(this),o.deleteProgram(C),this.program=void 0},this.type=n.shaderType,this.name=n.shaderName,this.id=_M++,this.cacheKey=e,this.usedTimes=1,this.program=C,this.vertexShader=F,this.fragmentShader=U,this}let HM=0;class GM{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){const n=e.vertexShader,r=e.fragmentShader,o=this._getShaderStage(n),u=this._getShaderStage(r),c=this._getShaderCacheForMaterial(e);return c.has(o)===!1&&(c.add(o),o.usedTimes++),c.has(u)===!1&&(c.add(u),u.usedTimes++),this}remove(e){const n=this.materialCache.get(e);for(const r of n)r.usedTimes--,r.usedTimes===0&&this.shaderCache.delete(r.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){const n=this.materialCache;let r=n.get(e);return r===void 0&&(r=new Set,n.set(e,r)),r}_getShaderStage(e){const n=this.shaderCache;let r=n.get(e);return r===void 0&&(r=new WM(e),n.set(e,r)),r}}class WM{constructor(e){this.id=HM++,this.code=e,this.usedTimes=0}}function XM(s,e,n,r,o,u){const c=new eg,d=new GM,p=new Set,m=[],x=new Map,S=r.logarithmicDepthBuffer;let g=r.precision;const y={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distance",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function M(A){return p.add(A),A===0?"uv":`uv${A}`}function C(A,D,fe,O,te){const Q=O.fog,oe=te.geometry,K=A.isMeshStandardMaterial||A.isMeshLambertMaterial||A.isMeshPhongMaterial?O.environment:null,ee=A.isMeshStandardMaterial||A.isMeshLambertMaterial&&!A.envMap||A.isMeshPhongMaterial&&!A.envMap,W=e.get(A.envMap||K,ee),q=W&&W.mapping===Bl?W.image.height:null,ae=y[A.type];A.precision!==null&&(g=r.getMaxPrecision(A.precision),g!==A.precision&&ot("WebGLProgram.getParameters:",A.precision,"not supported, using",g,"instead."));const le=oe.morphAttributes.position||oe.morphAttributes.normal||oe.morphAttributes.color,I=le!==void 0?le.length:0;let j=0;oe.morphAttributes.position!==void 0&&(j=1),oe.morphAttributes.normal!==void 0&&(j=2),oe.morphAttributes.color!==void 0&&(j=3);let Ce,Xe,Ze,ie;if(ae){const yt=Ti[ae];Ce=yt.vertexShader,Xe=yt.fragmentShader}else Ce=A.vertexShader,Xe=A.fragmentShader,d.update(A),Ze=d.getVertexShaderID(A),ie=d.getFragmentShaderID(A);const me=s.getRenderTarget(),pe=s.state.buffers.depth.getReversed(),Fe=te.isInstancedMesh===!0,He=te.isBatchedMesh===!0,nt=!!A.map,Wt=!!A.matcap,ht=!!W,xt=!!A.aoMap,Ct=!!A.lightMap,ut=!!A.bumpMap,Ft=!!A.normalMap,k=!!A.displacementMap,kt=!!A.emissiveMap,mt=!!A.metalnessMap,St=!!A.roughnessMap,Ge=A.anisotropy>0,P=A.clearcoat>0,E=A.dispersion>0,G=A.iridescence>0,de=A.sheen>0,ge=A.transmission>0,ue=Ge&&!!A.anisotropyMap,Be=P&&!!A.clearcoatMap,we=P&&!!A.clearcoatNormalMap,qe=P&&!!A.clearcoatRoughnessMap,it=G&&!!A.iridescenceMap,Se=G&&!!A.iridescenceThicknessMap,Te=de&&!!A.sheenColorMap,We=de&&!!A.sheenRoughnessMap,ke=!!A.specularMap,De=!!A.specularColorMap,lt=!!A.specularIntensityMap,V=ge&&!!A.transmissionMap,Ae=ge&&!!A.thicknessMap,Me=!!A.gradientMap,Le=!!A.alphaMap,ye=A.alphaTest>0,ce=!!A.alphaHash,ze=!!A.extensions;let rt=Ri;A.toneMapped&&(me===null||me.isXRRenderTarget===!0)&&(rt=s.toneMapping);const Pt={shaderID:ae,shaderType:A.type,shaderName:A.name,vertexShader:Ce,fragmentShader:Xe,defines:A.defines,customVertexShaderID:Ze,customFragmentShaderID:ie,isRawShaderMaterial:A.isRawShaderMaterial===!0,glslVersion:A.glslVersion,precision:g,batching:He,batchingColor:He&&te._colorsTexture!==null,instancing:Fe,instancingColor:Fe&&te.instanceColor!==null,instancingMorph:Fe&&te.morphTexture!==null,outputColorSpace:me===null?s.outputColorSpace:me.isXRRenderTarget===!0?me.texture.colorSpace:Xs,alphaToCoverage:!!A.alphaToCoverage,map:nt,matcap:Wt,envMap:ht,envMapMode:ht&&W.mapping,envMapCubeUVHeight:q,aoMap:xt,lightMap:Ct,bumpMap:ut,normalMap:Ft,displacementMap:k,emissiveMap:kt,normalMapObjectSpace:Ft&&A.normalMapType===N0,normalMapTangentSpace:Ft&&A.normalMapType===L0,metalnessMap:mt,roughnessMap:St,anisotropy:Ge,anisotropyMap:ue,clearcoat:P,clearcoatMap:Be,clearcoatNormalMap:we,clearcoatRoughnessMap:qe,dispersion:E,iridescence:G,iridescenceMap:it,iridescenceThicknessMap:Se,sheen:de,sheenColorMap:Te,sheenRoughnessMap:We,specularMap:ke,specularColorMap:De,specularIntensityMap:lt,transmission:ge,transmissionMap:V,thicknessMap:Ae,gradientMap:Me,opaque:A.transparent===!1&&A.blending===zs&&A.alphaToCoverage===!1,alphaMap:Le,alphaTest:ye,alphaHash:ce,combine:A.combine,mapUv:nt&&M(A.map.channel),aoMapUv:xt&&M(A.aoMap.channel),lightMapUv:Ct&&M(A.lightMap.channel),bumpMapUv:ut&&M(A.bumpMap.channel),normalMapUv:Ft&&M(A.normalMap.channel),displacementMapUv:k&&M(A.displacementMap.channel),emissiveMapUv:kt&&M(A.emissiveMap.channel),metalnessMapUv:mt&&M(A.metalnessMap.channel),roughnessMapUv:St&&M(A.roughnessMap.channel),anisotropyMapUv:ue&&M(A.anisotropyMap.channel),clearcoatMapUv:Be&&M(A.clearcoatMap.channel),clearcoatNormalMapUv:we&&M(A.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:qe&&M(A.clearcoatRoughnessMap.channel),iridescenceMapUv:it&&M(A.iridescenceMap.channel),iridescenceThicknessMapUv:Se&&M(A.iridescenceThicknessMap.channel),sheenColorMapUv:Te&&M(A.sheenColorMap.channel),sheenRoughnessMapUv:We&&M(A.sheenRoughnessMap.channel),specularMapUv:ke&&M(A.specularMap.channel),specularColorMapUv:De&&M(A.specularColorMap.channel),specularIntensityMapUv:lt&&M(A.specularIntensityMap.channel),transmissionMapUv:V&&M(A.transmissionMap.channel),thicknessMapUv:Ae&&M(A.thicknessMap.channel),alphaMapUv:Le&&M(A.alphaMap.channel),vertexTangents:!!oe.attributes.tangent&&(Ft||Ge),vertexColors:A.vertexColors,vertexAlphas:A.vertexColors===!0&&!!oe.attributes.color&&oe.attributes.color.itemSize===4,pointsUvs:te.isPoints===!0&&!!oe.attributes.uv&&(nt||Le),fog:!!Q,useFog:A.fog===!0,fogExp2:!!Q&&Q.isFogExp2,flatShading:A.wireframe===!1&&(A.flatShading===!0||oe.attributes.normal===void 0&&Ft===!1&&(A.isMeshLambertMaterial||A.isMeshPhongMaterial||A.isMeshStandardMaterial||A.isMeshPhysicalMaterial)),sizeAttenuation:A.sizeAttenuation===!0,logarithmicDepthBuffer:S,reversedDepthBuffer:pe,skinning:te.isSkinnedMesh===!0,morphTargets:oe.morphAttributes.position!==void 0,morphNormals:oe.morphAttributes.normal!==void 0,morphColors:oe.morphAttributes.color!==void 0,morphTargetsCount:I,morphTextureStride:j,numDirLights:D.directional.length,numPointLights:D.point.length,numSpotLights:D.spot.length,numSpotLightMaps:D.spotLightMap.length,numRectAreaLights:D.rectArea.length,numHemiLights:D.hemi.length,numDirLightShadows:D.directionalShadowMap.length,numPointLightShadows:D.pointShadowMap.length,numSpotLightShadows:D.spotShadowMap.length,numSpotLightShadowsWithMaps:D.numSpotLightShadowsWithMaps,numLightProbes:D.numLightProbes,numClippingPlanes:u.numPlanes,numClipIntersection:u.numIntersection,dithering:A.dithering,shadowMapEnabled:s.shadowMap.enabled&&fe.length>0,shadowMapType:s.shadowMap.type,toneMapping:rt,decodeVideoTexture:nt&&A.map.isVideoTexture===!0&&Et.getTransfer(A.map.colorSpace)===Dt,decodeVideoTextureEmissive:kt&&A.emissiveMap.isVideoTexture===!0&&Et.getTransfer(A.emissiveMap.colorSpace)===Dt,premultipliedAlpha:A.premultipliedAlpha,doubleSided:A.side===wi,flipSided:A.side===In,useDepthPacking:A.depthPacking>=0,depthPacking:A.depthPacking||0,index0AttributeName:A.index0AttributeName,extensionClipCullDistance:ze&&A.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(ze&&A.extensions.multiDraw===!0||He)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:A.customProgramCacheKey()};return Pt.vertexUv1s=p.has(1),Pt.vertexUv2s=p.has(2),Pt.vertexUv3s=p.has(3),p.clear(),Pt}function _(A){const D=[];if(A.shaderID?D.push(A.shaderID):(D.push(A.customVertexShaderID),D.push(A.customFragmentShaderID)),A.defines!==void 0)for(const fe in A.defines)D.push(fe),D.push(A.defines[fe]);return A.isRawShaderMaterial===!1&&(v(D,A),R(D,A),D.push(s.outputColorSpace)),D.push(A.customProgramCacheKey),D.join()}function v(A,D){A.push(D.precision),A.push(D.outputColorSpace),A.push(D.envMapMode),A.push(D.envMapCubeUVHeight),A.push(D.mapUv),A.push(D.alphaMapUv),A.push(D.lightMapUv),A.push(D.aoMapUv),A.push(D.bumpMapUv),A.push(D.normalMapUv),A.push(D.displacementMapUv),A.push(D.emissiveMapUv),A.push(D.metalnessMapUv),A.push(D.roughnessMapUv),A.push(D.anisotropyMapUv),A.push(D.clearcoatMapUv),A.push(D.clearcoatNormalMapUv),A.push(D.clearcoatRoughnessMapUv),A.push(D.iridescenceMapUv),A.push(D.iridescenceThicknessMapUv),A.push(D.sheenColorMapUv),A.push(D.sheenRoughnessMapUv),A.push(D.specularMapUv),A.push(D.specularColorMapUv),A.push(D.specularIntensityMapUv),A.push(D.transmissionMapUv),A.push(D.thicknessMapUv),A.push(D.combine),A.push(D.fogExp2),A.push(D.sizeAttenuation),A.push(D.morphTargetsCount),A.push(D.morphAttributeCount),A.push(D.numDirLights),A.push(D.numPointLights),A.push(D.numSpotLights),A.push(D.numSpotLightMaps),A.push(D.numHemiLights),A.push(D.numRectAreaLights),A.push(D.numDirLightShadows),A.push(D.numPointLightShadows),A.push(D.numSpotLightShadows),A.push(D.numSpotLightShadowsWithMaps),A.push(D.numLightProbes),A.push(D.shadowMapType),A.push(D.toneMapping),A.push(D.numClippingPlanes),A.push(D.numClipIntersection),A.push(D.depthPacking)}function R(A,D){c.disableAll(),D.instancing&&c.enable(0),D.instancingColor&&c.enable(1),D.instancingMorph&&c.enable(2),D.matcap&&c.enable(3),D.envMap&&c.enable(4),D.normalMapObjectSpace&&c.enable(5),D.normalMapTangentSpace&&c.enable(6),D.clearcoat&&c.enable(7),D.iridescence&&c.enable(8),D.alphaTest&&c.enable(9),D.vertexColors&&c.enable(10),D.vertexAlphas&&c.enable(11),D.vertexUv1s&&c.enable(12),D.vertexUv2s&&c.enable(13),D.vertexUv3s&&c.enable(14),D.vertexTangents&&c.enable(15),D.anisotropy&&c.enable(16),D.alphaHash&&c.enable(17),D.batching&&c.enable(18),D.dispersion&&c.enable(19),D.batchingColor&&c.enable(20),D.gradientMap&&c.enable(21),A.push(c.mask),c.disableAll(),D.fog&&c.enable(0),D.useFog&&c.enable(1),D.flatShading&&c.enable(2),D.logarithmicDepthBuffer&&c.enable(3),D.reversedDepthBuffer&&c.enable(4),D.skinning&&c.enable(5),D.morphTargets&&c.enable(6),D.morphNormals&&c.enable(7),D.morphColors&&c.enable(8),D.premultipliedAlpha&&c.enable(9),D.shadowMapEnabled&&c.enable(10),D.doubleSided&&c.enable(11),D.flipSided&&c.enable(12),D.useDepthPacking&&c.enable(13),D.dithering&&c.enable(14),D.transmission&&c.enable(15),D.sheen&&c.enable(16),D.opaque&&c.enable(17),D.pointsUvs&&c.enable(18),D.decodeVideoTexture&&c.enable(19),D.decodeVideoTextureEmissive&&c.enable(20),D.alphaToCoverage&&c.enable(21),A.push(c.mask)}function L(A){const D=y[A.type];let fe;if(D){const O=Ti[D];fe=_v.clone(O.uniforms)}else fe=A.uniforms;return fe}function b(A,D){let fe=x.get(D);return fe!==void 0?++fe.usedTimes:(fe=new VM(s,D,A,o),m.push(fe),x.set(D,fe)),fe}function F(A){if(--A.usedTimes===0){const D=m.indexOf(A);m[D]=m[m.length-1],m.pop(),x.delete(A.cacheKey),A.destroy()}}function U(A){d.remove(A)}function z(){d.dispose()}return{getParameters:C,getProgramCacheKey:_,getUniforms:L,acquireProgram:b,releaseProgram:F,releaseShaderCache:U,programs:m,dispose:z}}function jM(){let s=new WeakMap;function e(c){return s.has(c)}function n(c){let d=s.get(c);return d===void 0&&(d={},s.set(c,d)),d}function r(c){s.delete(c)}function o(c,d,p){s.get(c)[d]=p}function u(){s=new WeakMap}return{has:e,get:n,remove:r,update:o,dispose:u}}function YM(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.material.id!==e.material.id?s.material.id-e.material.id:s.materialVariant!==e.materialVariant?s.materialVariant-e.materialVariant:s.z!==e.z?s.z-e.z:s.id-e.id}function Dm(s,e){return s.groupOrder!==e.groupOrder?s.groupOrder-e.groupOrder:s.renderOrder!==e.renderOrder?s.renderOrder-e.renderOrder:s.z!==e.z?e.z-s.z:s.id-e.id}function Lm(){const s=[];let e=0;const n=[],r=[],o=[];function u(){e=0,n.length=0,r.length=0,o.length=0}function c(g){let y=0;return g.isInstancedMesh&&(y+=2),g.isSkinnedMesh&&(y+=1),y}function d(g,y,M,C,_,v){let R=s[e];return R===void 0?(R={id:g.id,object:g,geometry:y,material:M,materialVariant:c(g),groupOrder:C,renderOrder:g.renderOrder,z:_,group:v},s[e]=R):(R.id=g.id,R.object=g,R.geometry=y,R.material=M,R.materialVariant=c(g),R.groupOrder=C,R.renderOrder=g.renderOrder,R.z=_,R.group=v),e++,R}function p(g,y,M,C,_,v){const R=d(g,y,M,C,_,v);M.transmission>0?r.push(R):M.transparent===!0?o.push(R):n.push(R)}function m(g,y,M,C,_,v){const R=d(g,y,M,C,_,v);M.transmission>0?r.unshift(R):M.transparent===!0?o.unshift(R):n.unshift(R)}function x(g,y){n.length>1&&n.sort(g||YM),r.length>1&&r.sort(y||Dm),o.length>1&&o.sort(y||Dm)}function S(){for(let g=e,y=s.length;g<y;g++){const M=s[g];if(M.id===null)break;M.id=null,M.object=null,M.geometry=null,M.material=null,M.group=null}}return{opaque:n,transmissive:r,transparent:o,init:u,push:p,unshift:m,finish:S,sort:x}}function qM(){let s=new WeakMap;function e(r,o){const u=s.get(r);let c;return u===void 0?(c=new Lm,s.set(r,[c])):o>=u.length?(c=new Lm,u.push(c)):c=u[o],c}function n(){s=new WeakMap}return{get:e,dispose:n}}function $M(){const s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let n;switch(e.type){case"DirectionalLight":n={direction:new ne,color:new bt};break;case"SpotLight":n={position:new ne,direction:new ne,color:new bt,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":n={position:new ne,color:new bt,distance:0,decay:0};break;case"HemisphereLight":n={direction:new ne,skyColor:new bt,groundColor:new bt};break;case"RectAreaLight":n={color:new bt,position:new ne,halfWidth:new ne,halfHeight:new ne};break}return s[e.id]=n,n}}}function KM(){const s={};return{get:function(e){if(s[e.id]!==void 0)return s[e.id];let n;switch(e.type){case"DirectionalLight":n={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Lt};break;case"SpotLight":n={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Lt};break;case"PointLight":n={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Lt,shadowCameraNear:1,shadowCameraFar:1e3};break}return s[e.id]=n,n}}}let ZM=0;function QM(s,e){return(e.castShadow?2:0)-(s.castShadow?2:0)+(e.map?1:0)-(s.map?1:0)}function JM(s){const e=new $M,n=KM(),r={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let m=0;m<9;m++)r.probe.push(new ne);const o=new ne,u=new $t,c=new $t;function d(m){let x=0,S=0,g=0;for(let D=0;D<9;D++)r.probe[D].set(0,0,0);let y=0,M=0,C=0,_=0,v=0,R=0,L=0,b=0,F=0,U=0,z=0;m.sort(QM);for(let D=0,fe=m.length;D<fe;D++){const O=m[D],te=O.color,Q=O.intensity,oe=O.distance;let K=null;if(O.shadow&&O.shadow.map&&(O.shadow.map.texture.format===Ws?K=O.shadow.map.texture:K=O.shadow.map.depthTexture||O.shadow.map.texture),O.isAmbientLight)x+=te.r*Q,S+=te.g*Q,g+=te.b*Q;else if(O.isLightProbe){for(let ee=0;ee<9;ee++)r.probe[ee].addScaledVector(O.sh.coefficients[ee],Q);z++}else if(O.isDirectionalLight){const ee=e.get(O);if(ee.color.copy(O.color).multiplyScalar(O.intensity),O.castShadow){const W=O.shadow,q=n.get(O);q.shadowIntensity=W.intensity,q.shadowBias=W.bias,q.shadowNormalBias=W.normalBias,q.shadowRadius=W.radius,q.shadowMapSize=W.mapSize,r.directionalShadow[y]=q,r.directionalShadowMap[y]=K,r.directionalShadowMatrix[y]=O.shadow.matrix,R++}r.directional[y]=ee,y++}else if(O.isSpotLight){const ee=e.get(O);ee.position.setFromMatrixPosition(O.matrixWorld),ee.color.copy(te).multiplyScalar(Q),ee.distance=oe,ee.coneCos=Math.cos(O.angle),ee.penumbraCos=Math.cos(O.angle*(1-O.penumbra)),ee.decay=O.decay,r.spot[C]=ee;const W=O.shadow;if(O.map&&(r.spotLightMap[F]=O.map,F++,W.updateMatrices(O),O.castShadow&&U++),r.spotLightMatrix[C]=W.matrix,O.castShadow){const q=n.get(O);q.shadowIntensity=W.intensity,q.shadowBias=W.bias,q.shadowNormalBias=W.normalBias,q.shadowRadius=W.radius,q.shadowMapSize=W.mapSize,r.spotShadow[C]=q,r.spotShadowMap[C]=K,b++}C++}else if(O.isRectAreaLight){const ee=e.get(O);ee.color.copy(te).multiplyScalar(Q),ee.halfWidth.set(O.width*.5,0,0),ee.halfHeight.set(0,O.height*.5,0),r.rectArea[_]=ee,_++}else if(O.isPointLight){const ee=e.get(O);if(ee.color.copy(O.color).multiplyScalar(O.intensity),ee.distance=O.distance,ee.decay=O.decay,O.castShadow){const W=O.shadow,q=n.get(O);q.shadowIntensity=W.intensity,q.shadowBias=W.bias,q.shadowNormalBias=W.normalBias,q.shadowRadius=W.radius,q.shadowMapSize=W.mapSize,q.shadowCameraNear=W.camera.near,q.shadowCameraFar=W.camera.far,r.pointShadow[M]=q,r.pointShadowMap[M]=K,r.pointShadowMatrix[M]=O.shadow.matrix,L++}r.point[M]=ee,M++}else if(O.isHemisphereLight){const ee=e.get(O);ee.skyColor.copy(O.color).multiplyScalar(Q),ee.groundColor.copy(O.groundColor).multiplyScalar(Q),r.hemi[v]=ee,v++}}_>0&&(s.has("OES_texture_float_linear")===!0?(r.rectAreaLTC1=Pe.LTC_FLOAT_1,r.rectAreaLTC2=Pe.LTC_FLOAT_2):(r.rectAreaLTC1=Pe.LTC_HALF_1,r.rectAreaLTC2=Pe.LTC_HALF_2)),r.ambient[0]=x,r.ambient[1]=S,r.ambient[2]=g;const A=r.hash;(A.directionalLength!==y||A.pointLength!==M||A.spotLength!==C||A.rectAreaLength!==_||A.hemiLength!==v||A.numDirectionalShadows!==R||A.numPointShadows!==L||A.numSpotShadows!==b||A.numSpotMaps!==F||A.numLightProbes!==z)&&(r.directional.length=y,r.spot.length=C,r.rectArea.length=_,r.point.length=M,r.hemi.length=v,r.directionalShadow.length=R,r.directionalShadowMap.length=R,r.pointShadow.length=L,r.pointShadowMap.length=L,r.spotShadow.length=b,r.spotShadowMap.length=b,r.directionalShadowMatrix.length=R,r.pointShadowMatrix.length=L,r.spotLightMatrix.length=b+F-U,r.spotLightMap.length=F,r.numSpotLightShadowsWithMaps=U,r.numLightProbes=z,A.directionalLength=y,A.pointLength=M,A.spotLength=C,A.rectAreaLength=_,A.hemiLength=v,A.numDirectionalShadows=R,A.numPointShadows=L,A.numSpotShadows=b,A.numSpotMaps=F,A.numLightProbes=z,r.version=ZM++)}function p(m,x){let S=0,g=0,y=0,M=0,C=0;const _=x.matrixWorldInverse;for(let v=0,R=m.length;v<R;v++){const L=m[v];if(L.isDirectionalLight){const b=r.directional[S];b.direction.setFromMatrixPosition(L.matrixWorld),o.setFromMatrixPosition(L.target.matrixWorld),b.direction.sub(o),b.direction.transformDirection(_),S++}else if(L.isSpotLight){const b=r.spot[y];b.position.setFromMatrixPosition(L.matrixWorld),b.position.applyMatrix4(_),b.direction.setFromMatrixPosition(L.matrixWorld),o.setFromMatrixPosition(L.target.matrixWorld),b.direction.sub(o),b.direction.transformDirection(_),y++}else if(L.isRectAreaLight){const b=r.rectArea[M];b.position.setFromMatrixPosition(L.matrixWorld),b.position.applyMatrix4(_),c.identity(),u.copy(L.matrixWorld),u.premultiply(_),c.extractRotation(u),b.halfWidth.set(L.width*.5,0,0),b.halfHeight.set(0,L.height*.5,0),b.halfWidth.applyMatrix4(c),b.halfHeight.applyMatrix4(c),M++}else if(L.isPointLight){const b=r.point[g];b.position.setFromMatrixPosition(L.matrixWorld),b.position.applyMatrix4(_),g++}else if(L.isHemisphereLight){const b=r.hemi[C];b.direction.setFromMatrixPosition(L.matrixWorld),b.direction.transformDirection(_),C++}}}return{setup:d,setupView:p,state:r}}function Nm(s){const e=new JM(s),n=[],r=[];function o(x){m.camera=x,n.length=0,r.length=0}function u(x){n.push(x)}function c(x){r.push(x)}function d(){e.setup(n)}function p(x){e.setupView(n,x)}const m={lightsArray:n,shadowsArray:r,camera:null,lights:e,transmissionRenderTarget:{}};return{init:o,state:m,setupLights:d,setupLightsView:p,pushLight:u,pushShadow:c}}function eE(s){let e=new WeakMap;function n(o,u=0){const c=e.get(o);let d;return c===void 0?(d=new Nm(s),e.set(o,[d])):u>=c.length?(d=new Nm(s),c.push(d)):d=c[u],d}function r(){e=new WeakMap}return{get:n,dispose:r}}const tE=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,nE=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ).rg;
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ).r;
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( max( 0.0, squared_mean - mean * mean ) );
	gl_FragColor = vec4( mean, std_dev, 0.0, 1.0 );
}`,iE=[new ne(1,0,0),new ne(-1,0,0),new ne(0,1,0),new ne(0,-1,0),new ne(0,0,1),new ne(0,0,-1)],rE=[new ne(0,-1,0),new ne(0,-1,0),new ne(0,0,1),new ne(0,0,-1),new ne(0,-1,0),new ne(0,-1,0)],Im=new $t,Fa=new ne,sf=new ne;function sE(s,e,n){let r=new sg;const o=new Lt,u=new Lt,c=new qt,d=new yv,p=new Mv,m={},x=n.maxTextureSize,S={[Rr]:In,[In]:Rr,[wi]:wi},g=new Di({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new Lt},radius:{value:4}},vertexShader:tE,fragmentShader:nE}),y=g.clone();y.defines.HORIZONTAL_PASS=1;const M=new Gn;M.setAttribute("position",new gi(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const C=new ii(M,g),_=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Cl;let v=this.type;this.render=function(U,z,A){if(_.enabled===!1||_.autoUpdate===!1&&_.needsUpdate===!1||U.length===0)return;this.type===u0&&(ot("WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead."),this.type=Cl);const D=s.getRenderTarget(),fe=s.getActiveCubeFace(),O=s.getActiveMipmapLevel(),te=s.state;te.setBlending(qi),te.buffers.depth.getReversed()===!0?te.buffers.color.setClear(0,0,0,0):te.buffers.color.setClear(1,1,1,1),te.buffers.depth.setTest(!0),te.setScissorTest(!1);const Q=v!==this.type;Q&&z.traverse(function(oe){oe.material&&(Array.isArray(oe.material)?oe.material.forEach(K=>K.needsUpdate=!0):oe.material.needsUpdate=!0)});for(let oe=0,K=U.length;oe<K;oe++){const ee=U[oe],W=ee.shadow;if(W===void 0){ot("WebGLShadowMap:",ee,"has no shadow.");continue}if(W.autoUpdate===!1&&W.needsUpdate===!1)continue;o.copy(W.mapSize);const q=W.getFrameExtents();o.multiply(q),u.copy(W.mapSize),(o.x>x||o.y>x)&&(o.x>x&&(u.x=Math.floor(x/q.x),o.x=u.x*q.x,W.mapSize.x=u.x),o.y>x&&(u.y=Math.floor(x/q.y),o.y=u.y*q.y,W.mapSize.y=u.y));const ae=s.state.buffers.depth.getReversed();if(W.camera._reversedDepth=ae,W.map===null||Q===!0){if(W.map!==null&&(W.map.depthTexture!==null&&(W.map.depthTexture.dispose(),W.map.depthTexture=null),W.map.dispose()),this.type===Oa){if(ee.isPointLight){ot("WebGLShadowMap: VSM shadow maps are not supported for PointLights. Use PCF or BasicShadowMap instead.");continue}W.map=new bi(o.x,o.y,{format:Ws,type:Ki,minFilter:_n,magFilter:_n,generateMipmaps:!1}),W.map.texture.name=ee.name+".shadowMap",W.map.depthTexture=new Ha(o.x,o.y,Ai),W.map.depthTexture.name=ee.name+".shadowMapDepth",W.map.depthTexture.format=Zi,W.map.depthTexture.compareFunction=null,W.map.depthTexture.minFilter=cn,W.map.depthTexture.magFilter=cn}else ee.isPointLight?(W.map=new hg(o.x),W.map.depthTexture=new mv(o.x,Pi)):(W.map=new bi(o.x,o.y),W.map.depthTexture=new Ha(o.x,o.y,Pi)),W.map.depthTexture.name=ee.name+".shadowMap",W.map.depthTexture.format=Zi,this.type===Cl?(W.map.depthTexture.compareFunction=ae?ld:od,W.map.depthTexture.minFilter=_n,W.map.depthTexture.magFilter=_n):(W.map.depthTexture.compareFunction=null,W.map.depthTexture.minFilter=cn,W.map.depthTexture.magFilter=cn);W.camera.updateProjectionMatrix()}const le=W.map.isWebGLCubeRenderTarget?6:1;for(let I=0;I<le;I++){if(W.map.isWebGLCubeRenderTarget)s.setRenderTarget(W.map,I),s.clear();else{I===0&&(s.setRenderTarget(W.map),s.clear());const j=W.getViewport(I);c.set(u.x*j.x,u.y*j.y,u.x*j.z,u.y*j.w),te.viewport(c)}if(ee.isPointLight){const j=W.camera,Ce=W.matrix,Xe=ee.distance||j.far;Xe!==j.far&&(j.far=Xe,j.updateProjectionMatrix()),Fa.setFromMatrixPosition(ee.matrixWorld),j.position.copy(Fa),sf.copy(j.position),sf.add(iE[I]),j.up.copy(rE[I]),j.lookAt(sf),j.updateMatrixWorld(),Ce.makeTranslation(-Fa.x,-Fa.y,-Fa.z),Im.multiplyMatrices(j.projectionMatrix,j.matrixWorldInverse),W._frustum.setFromProjectionMatrix(Im,j.coordinateSystem,j.reversedDepth)}else W.updateMatrices(ee);r=W.getFrustum(),b(z,A,W.camera,ee,this.type)}W.isPointLightShadow!==!0&&this.type===Oa&&R(W,A),W.needsUpdate=!1}v=this.type,_.needsUpdate=!1,s.setRenderTarget(D,fe,O)};function R(U,z){const A=e.update(C);g.defines.VSM_SAMPLES!==U.blurSamples&&(g.defines.VSM_SAMPLES=U.blurSamples,y.defines.VSM_SAMPLES=U.blurSamples,g.needsUpdate=!0,y.needsUpdate=!0),U.mapPass===null&&(U.mapPass=new bi(o.x,o.y,{format:Ws,type:Ki})),g.uniforms.shadow_pass.value=U.map.depthTexture,g.uniforms.resolution.value=U.mapSize,g.uniforms.radius.value=U.radius,s.setRenderTarget(U.mapPass),s.clear(),s.renderBufferDirect(z,null,A,g,C,null),y.uniforms.shadow_pass.value=U.mapPass.texture,y.uniforms.resolution.value=U.mapSize,y.uniforms.radius.value=U.radius,s.setRenderTarget(U.map),s.clear(),s.renderBufferDirect(z,null,A,y,C,null)}function L(U,z,A,D){let fe=null;const O=A.isPointLight===!0?U.customDistanceMaterial:U.customDepthMaterial;if(O!==void 0)fe=O;else if(fe=A.isPointLight===!0?p:d,s.localClippingEnabled&&z.clipShadows===!0&&Array.isArray(z.clippingPlanes)&&z.clippingPlanes.length!==0||z.displacementMap&&z.displacementScale!==0||z.alphaMap&&z.alphaTest>0||z.map&&z.alphaTest>0||z.alphaToCoverage===!0){const te=fe.uuid,Q=z.uuid;let oe=m[te];oe===void 0&&(oe={},m[te]=oe);let K=oe[Q];K===void 0&&(K=fe.clone(),oe[Q]=K,z.addEventListener("dispose",F)),fe=K}if(fe.visible=z.visible,fe.wireframe=z.wireframe,D===Oa?fe.side=z.shadowSide!==null?z.shadowSide:z.side:fe.side=z.shadowSide!==null?z.shadowSide:S[z.side],fe.alphaMap=z.alphaMap,fe.alphaTest=z.alphaToCoverage===!0?.5:z.alphaTest,fe.map=z.map,fe.clipShadows=z.clipShadows,fe.clippingPlanes=z.clippingPlanes,fe.clipIntersection=z.clipIntersection,fe.displacementMap=z.displacementMap,fe.displacementScale=z.displacementScale,fe.displacementBias=z.displacementBias,fe.wireframeLinewidth=z.wireframeLinewidth,fe.linewidth=z.linewidth,A.isPointLight===!0&&fe.isMeshDistanceMaterial===!0){const te=s.properties.get(fe);te.light=A}return fe}function b(U,z,A,D,fe){if(U.visible===!1)return;if(U.layers.test(z.layers)&&(U.isMesh||U.isLine||U.isPoints)&&(U.castShadow||U.receiveShadow&&fe===Oa)&&(!U.frustumCulled||r.intersectsObject(U))){U.modelViewMatrix.multiplyMatrices(A.matrixWorldInverse,U.matrixWorld);const Q=e.update(U),oe=U.material;if(Array.isArray(oe)){const K=Q.groups;for(let ee=0,W=K.length;ee<W;ee++){const q=K[ee],ae=oe[q.materialIndex];if(ae&&ae.visible){const le=L(U,ae,D,fe);U.onBeforeShadow(s,U,z,A,Q,le,q),s.renderBufferDirect(A,null,Q,le,U,q),U.onAfterShadow(s,U,z,A,Q,le,q)}}}else if(oe.visible){const K=L(U,oe,D,fe);U.onBeforeShadow(s,U,z,A,Q,K,null),s.renderBufferDirect(A,null,Q,K,U,null),U.onAfterShadow(s,U,z,A,Q,K,null)}}const te=U.children;for(let Q=0,oe=te.length;Q<oe;Q++)b(te[Q],z,A,D,fe)}function F(U){U.target.removeEventListener("dispose",F);for(const A in m){const D=m[A],fe=U.target.uuid;fe in D&&(D[fe].dispose(),delete D[fe])}}}function aE(s,e){function n(){let V=!1;const Ae=new qt;let Me=null;const Le=new qt(0,0,0,0);return{setMask:function(ye){Me!==ye&&!V&&(s.colorMask(ye,ye,ye,ye),Me=ye)},setLocked:function(ye){V=ye},setClear:function(ye,ce,ze,rt,Pt){Pt===!0&&(ye*=rt,ce*=rt,ze*=rt),Ae.set(ye,ce,ze,rt),Le.equals(Ae)===!1&&(s.clearColor(ye,ce,ze,rt),Le.copy(Ae))},reset:function(){V=!1,Me=null,Le.set(-1,0,0,0)}}}function r(){let V=!1,Ae=!1,Me=null,Le=null,ye=null;return{setReversed:function(ce){if(Ae!==ce){const ze=e.get("EXT_clip_control");ce?ze.clipControlEXT(ze.LOWER_LEFT_EXT,ze.ZERO_TO_ONE_EXT):ze.clipControlEXT(ze.LOWER_LEFT_EXT,ze.NEGATIVE_ONE_TO_ONE_EXT),Ae=ce;const rt=ye;ye=null,this.setClear(rt)}},getReversed:function(){return Ae},setTest:function(ce){ce?me(s.DEPTH_TEST):pe(s.DEPTH_TEST)},setMask:function(ce){Me!==ce&&!V&&(s.depthMask(ce),Me=ce)},setFunc:function(ce){if(Ae&&(ce=G0[ce]),Le!==ce){switch(ce){case lf:s.depthFunc(s.NEVER);break;case uf:s.depthFunc(s.ALWAYS);break;case cf:s.depthFunc(s.LESS);break;case Hs:s.depthFunc(s.LEQUAL);break;case ff:s.depthFunc(s.EQUAL);break;case df:s.depthFunc(s.GEQUAL);break;case hf:s.depthFunc(s.GREATER);break;case pf:s.depthFunc(s.NOTEQUAL);break;default:s.depthFunc(s.LEQUAL)}Le=ce}},setLocked:function(ce){V=ce},setClear:function(ce){ye!==ce&&(ye=ce,Ae&&(ce=1-ce),s.clearDepth(ce))},reset:function(){V=!1,Me=null,Le=null,ye=null,Ae=!1}}}function o(){let V=!1,Ae=null,Me=null,Le=null,ye=null,ce=null,ze=null,rt=null,Pt=null;return{setTest:function(yt){V||(yt?me(s.STENCIL_TEST):pe(s.STENCIL_TEST))},setMask:function(yt){Ae!==yt&&!V&&(s.stencilMask(yt),Ae=yt)},setFunc:function(yt,Wn,vn){(Me!==yt||Le!==Wn||ye!==vn)&&(s.stencilFunc(yt,Wn,vn),Me=yt,Le=Wn,ye=vn)},setOp:function(yt,Wn,vn){(ce!==yt||ze!==Wn||rt!==vn)&&(s.stencilOp(yt,Wn,vn),ce=yt,ze=Wn,rt=vn)},setLocked:function(yt){V=yt},setClear:function(yt){Pt!==yt&&(s.clearStencil(yt),Pt=yt)},reset:function(){V=!1,Ae=null,Me=null,Le=null,ye=null,ce=null,ze=null,rt=null,Pt=null}}}const u=new n,c=new r,d=new o,p=new WeakMap,m=new WeakMap;let x={},S={},g=new WeakMap,y=[],M=null,C=!1,_=null,v=null,R=null,L=null,b=null,F=null,U=null,z=new bt(0,0,0),A=0,D=!1,fe=null,O=null,te=null,Q=null,oe=null;const K=s.getParameter(s.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let ee=!1,W=0;const q=s.getParameter(s.VERSION);q.indexOf("WebGL")!==-1?(W=parseFloat(/^WebGL (\d)/.exec(q)[1]),ee=W>=1):q.indexOf("OpenGL ES")!==-1&&(W=parseFloat(/^OpenGL ES (\d)/.exec(q)[1]),ee=W>=2);let ae=null,le={};const I=s.getParameter(s.SCISSOR_BOX),j=s.getParameter(s.VIEWPORT),Ce=new qt().fromArray(I),Xe=new qt().fromArray(j);function Ze(V,Ae,Me,Le){const ye=new Uint8Array(4),ce=s.createTexture();s.bindTexture(V,ce),s.texParameteri(V,s.TEXTURE_MIN_FILTER,s.NEAREST),s.texParameteri(V,s.TEXTURE_MAG_FILTER,s.NEAREST);for(let ze=0;ze<Me;ze++)V===s.TEXTURE_3D||V===s.TEXTURE_2D_ARRAY?s.texImage3D(Ae,0,s.RGBA,1,1,Le,0,s.RGBA,s.UNSIGNED_BYTE,ye):s.texImage2D(Ae+ze,0,s.RGBA,1,1,0,s.RGBA,s.UNSIGNED_BYTE,ye);return ce}const ie={};ie[s.TEXTURE_2D]=Ze(s.TEXTURE_2D,s.TEXTURE_2D,1),ie[s.TEXTURE_CUBE_MAP]=Ze(s.TEXTURE_CUBE_MAP,s.TEXTURE_CUBE_MAP_POSITIVE_X,6),ie[s.TEXTURE_2D_ARRAY]=Ze(s.TEXTURE_2D_ARRAY,s.TEXTURE_2D_ARRAY,1,1),ie[s.TEXTURE_3D]=Ze(s.TEXTURE_3D,s.TEXTURE_3D,1,1),u.setClear(0,0,0,1),c.setClear(1),d.setClear(0),me(s.DEPTH_TEST),c.setFunc(Hs),ut(!1),Ft(Bp),me(s.CULL_FACE),xt(qi);function me(V){x[V]!==!0&&(s.enable(V),x[V]=!0)}function pe(V){x[V]!==!1&&(s.disable(V),x[V]=!1)}function Fe(V,Ae){return S[V]!==Ae?(s.bindFramebuffer(V,Ae),S[V]=Ae,V===s.DRAW_FRAMEBUFFER&&(S[s.FRAMEBUFFER]=Ae),V===s.FRAMEBUFFER&&(S[s.DRAW_FRAMEBUFFER]=Ae),!0):!1}function He(V,Ae){let Me=y,Le=!1;if(V){Me=g.get(Ae),Me===void 0&&(Me=[],g.set(Ae,Me));const ye=V.textures;if(Me.length!==ye.length||Me[0]!==s.COLOR_ATTACHMENT0){for(let ce=0,ze=ye.length;ce<ze;ce++)Me[ce]=s.COLOR_ATTACHMENT0+ce;Me.length=ye.length,Le=!0}}else Me[0]!==s.BACK&&(Me[0]=s.BACK,Le=!0);Le&&s.drawBuffers(Me)}function nt(V){return M!==V?(s.useProgram(V),M=V,!0):!1}const Wt={[Zr]:s.FUNC_ADD,[f0]:s.FUNC_SUBTRACT,[d0]:s.FUNC_REVERSE_SUBTRACT};Wt[h0]=s.MIN,Wt[p0]=s.MAX;const ht={[m0]:s.ZERO,[g0]:s.ONE,[_0]:s.SRC_COLOR,[af]:s.SRC_ALPHA,[E0]:s.SRC_ALPHA_SATURATE,[y0]:s.DST_COLOR,[x0]:s.DST_ALPHA,[v0]:s.ONE_MINUS_SRC_COLOR,[of]:s.ONE_MINUS_SRC_ALPHA,[M0]:s.ONE_MINUS_DST_COLOR,[S0]:s.ONE_MINUS_DST_ALPHA,[T0]:s.CONSTANT_COLOR,[w0]:s.ONE_MINUS_CONSTANT_COLOR,[A0]:s.CONSTANT_ALPHA,[C0]:s.ONE_MINUS_CONSTANT_ALPHA};function xt(V,Ae,Me,Le,ye,ce,ze,rt,Pt,yt){if(V===qi){C===!0&&(pe(s.BLEND),C=!1);return}if(C===!1&&(me(s.BLEND),C=!0),V!==c0){if(V!==_||yt!==D){if((v!==Zr||b!==Zr)&&(s.blendEquation(s.FUNC_ADD),v=Zr,b=Zr),yt)switch(V){case zs:s.blendFuncSeparate(s.ONE,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case kp:s.blendFunc(s.ONE,s.ONE);break;case zp:s.blendFuncSeparate(s.ZERO,s.ONE_MINUS_SRC_COLOR,s.ZERO,s.ONE);break;case Vp:s.blendFuncSeparate(s.DST_COLOR,s.ONE_MINUS_SRC_ALPHA,s.ZERO,s.ONE);break;default:wt("WebGLState: Invalid blending: ",V);break}else switch(V){case zs:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE_MINUS_SRC_ALPHA,s.ONE,s.ONE_MINUS_SRC_ALPHA);break;case kp:s.blendFuncSeparate(s.SRC_ALPHA,s.ONE,s.ONE,s.ONE);break;case zp:wt("WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case Vp:wt("WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:wt("WebGLState: Invalid blending: ",V);break}R=null,L=null,F=null,U=null,z.set(0,0,0),A=0,_=V,D=yt}return}ye=ye||Ae,ce=ce||Me,ze=ze||Le,(Ae!==v||ye!==b)&&(s.blendEquationSeparate(Wt[Ae],Wt[ye]),v=Ae,b=ye),(Me!==R||Le!==L||ce!==F||ze!==U)&&(s.blendFuncSeparate(ht[Me],ht[Le],ht[ce],ht[ze]),R=Me,L=Le,F=ce,U=ze),(rt.equals(z)===!1||Pt!==A)&&(s.blendColor(rt.r,rt.g,rt.b,Pt),z.copy(rt),A=Pt),_=V,D=!1}function Ct(V,Ae){V.side===wi?pe(s.CULL_FACE):me(s.CULL_FACE);let Me=V.side===In;Ae&&(Me=!Me),ut(Me),V.blending===zs&&V.transparent===!1?xt(qi):xt(V.blending,V.blendEquation,V.blendSrc,V.blendDst,V.blendEquationAlpha,V.blendSrcAlpha,V.blendDstAlpha,V.blendColor,V.blendAlpha,V.premultipliedAlpha),c.setFunc(V.depthFunc),c.setTest(V.depthTest),c.setMask(V.depthWrite),u.setMask(V.colorWrite);const Le=V.stencilWrite;d.setTest(Le),Le&&(d.setMask(V.stencilWriteMask),d.setFunc(V.stencilFunc,V.stencilRef,V.stencilFuncMask),d.setOp(V.stencilFail,V.stencilZFail,V.stencilZPass)),kt(V.polygonOffset,V.polygonOffsetFactor,V.polygonOffsetUnits),V.alphaToCoverage===!0?me(s.SAMPLE_ALPHA_TO_COVERAGE):pe(s.SAMPLE_ALPHA_TO_COVERAGE)}function ut(V){fe!==V&&(V?s.frontFace(s.CW):s.frontFace(s.CCW),fe=V)}function Ft(V){V!==o0?(me(s.CULL_FACE),V!==O&&(V===Bp?s.cullFace(s.BACK):V===l0?s.cullFace(s.FRONT):s.cullFace(s.FRONT_AND_BACK))):pe(s.CULL_FACE),O=V}function k(V){V!==te&&(ee&&s.lineWidth(V),te=V)}function kt(V,Ae,Me){V?(me(s.POLYGON_OFFSET_FILL),(Q!==Ae||oe!==Me)&&(Q=Ae,oe=Me,c.getReversed()&&(Ae=-Ae),s.polygonOffset(Ae,Me))):pe(s.POLYGON_OFFSET_FILL)}function mt(V){V?me(s.SCISSOR_TEST):pe(s.SCISSOR_TEST)}function St(V){V===void 0&&(V=s.TEXTURE0+K-1),ae!==V&&(s.activeTexture(V),ae=V)}function Ge(V,Ae,Me){Me===void 0&&(ae===null?Me=s.TEXTURE0+K-1:Me=ae);let Le=le[Me];Le===void 0&&(Le={type:void 0,texture:void 0},le[Me]=Le),(Le.type!==V||Le.texture!==Ae)&&(ae!==Me&&(s.activeTexture(Me),ae=Me),s.bindTexture(V,Ae||ie[V]),Le.type=V,Le.texture=Ae)}function P(){const V=le[ae];V!==void 0&&V.type!==void 0&&(s.bindTexture(V.type,null),V.type=void 0,V.texture=void 0)}function E(){try{s.compressedTexImage2D(...arguments)}catch(V){wt("WebGLState:",V)}}function G(){try{s.compressedTexImage3D(...arguments)}catch(V){wt("WebGLState:",V)}}function de(){try{s.texSubImage2D(...arguments)}catch(V){wt("WebGLState:",V)}}function ge(){try{s.texSubImage3D(...arguments)}catch(V){wt("WebGLState:",V)}}function ue(){try{s.compressedTexSubImage2D(...arguments)}catch(V){wt("WebGLState:",V)}}function Be(){try{s.compressedTexSubImage3D(...arguments)}catch(V){wt("WebGLState:",V)}}function we(){try{s.texStorage2D(...arguments)}catch(V){wt("WebGLState:",V)}}function qe(){try{s.texStorage3D(...arguments)}catch(V){wt("WebGLState:",V)}}function it(){try{s.texImage2D(...arguments)}catch(V){wt("WebGLState:",V)}}function Se(){try{s.texImage3D(...arguments)}catch(V){wt("WebGLState:",V)}}function Te(V){Ce.equals(V)===!1&&(s.scissor(V.x,V.y,V.z,V.w),Ce.copy(V))}function We(V){Xe.equals(V)===!1&&(s.viewport(V.x,V.y,V.z,V.w),Xe.copy(V))}function ke(V,Ae){let Me=m.get(Ae);Me===void 0&&(Me=new WeakMap,m.set(Ae,Me));let Le=Me.get(V);Le===void 0&&(Le=s.getUniformBlockIndex(Ae,V.name),Me.set(V,Le))}function De(V,Ae){const Le=m.get(Ae).get(V);p.get(Ae)!==Le&&(s.uniformBlockBinding(Ae,Le,V.__bindingPointIndex),p.set(Ae,Le))}function lt(){s.disable(s.BLEND),s.disable(s.CULL_FACE),s.disable(s.DEPTH_TEST),s.disable(s.POLYGON_OFFSET_FILL),s.disable(s.SCISSOR_TEST),s.disable(s.STENCIL_TEST),s.disable(s.SAMPLE_ALPHA_TO_COVERAGE),s.blendEquation(s.FUNC_ADD),s.blendFunc(s.ONE,s.ZERO),s.blendFuncSeparate(s.ONE,s.ZERO,s.ONE,s.ZERO),s.blendColor(0,0,0,0),s.colorMask(!0,!0,!0,!0),s.clearColor(0,0,0,0),s.depthMask(!0),s.depthFunc(s.LESS),c.setReversed(!1),s.clearDepth(1),s.stencilMask(4294967295),s.stencilFunc(s.ALWAYS,0,4294967295),s.stencilOp(s.KEEP,s.KEEP,s.KEEP),s.clearStencil(0),s.cullFace(s.BACK),s.frontFace(s.CCW),s.polygonOffset(0,0),s.activeTexture(s.TEXTURE0),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),s.bindFramebuffer(s.READ_FRAMEBUFFER,null),s.useProgram(null),s.lineWidth(1),s.scissor(0,0,s.canvas.width,s.canvas.height),s.viewport(0,0,s.canvas.width,s.canvas.height),x={},ae=null,le={},S={},g=new WeakMap,y=[],M=null,C=!1,_=null,v=null,R=null,L=null,b=null,F=null,U=null,z=new bt(0,0,0),A=0,D=!1,fe=null,O=null,te=null,Q=null,oe=null,Ce.set(0,0,s.canvas.width,s.canvas.height),Xe.set(0,0,s.canvas.width,s.canvas.height),u.reset(),c.reset(),d.reset()}return{buffers:{color:u,depth:c,stencil:d},enable:me,disable:pe,bindFramebuffer:Fe,drawBuffers:He,useProgram:nt,setBlending:xt,setMaterial:Ct,setFlipSided:ut,setCullFace:Ft,setLineWidth:k,setPolygonOffset:kt,setScissorTest:mt,activeTexture:St,bindTexture:Ge,unbindTexture:P,compressedTexImage2D:E,compressedTexImage3D:G,texImage2D:it,texImage3D:Se,updateUBOMapping:ke,uniformBlockBinding:De,texStorage2D:we,texStorage3D:qe,texSubImage2D:de,texSubImage3D:ge,compressedTexSubImage2D:ue,compressedTexSubImage3D:Be,scissor:Te,viewport:We,reset:lt}}function oE(s,e,n,r,o,u,c){const d=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,p=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),m=new Lt,x=new WeakMap;let S;const g=new WeakMap;let y=!1;try{y=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function M(P,E){return y?new OffscreenCanvas(P,E):Ul("canvas")}function C(P,E,G){let de=1;const ge=Ge(P);if((ge.width>G||ge.height>G)&&(de=G/Math.max(ge.width,ge.height)),de<1)if(typeof HTMLImageElement<"u"&&P instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&P instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&P instanceof ImageBitmap||typeof VideoFrame<"u"&&P instanceof VideoFrame){const ue=Math.floor(de*ge.width),Be=Math.floor(de*ge.height);S===void 0&&(S=M(ue,Be));const we=E?M(ue,Be):S;return we.width=ue,we.height=Be,we.getContext("2d").drawImage(P,0,0,ue,Be),ot("WebGLRenderer: Texture has been resized from ("+ge.width+"x"+ge.height+") to ("+ue+"x"+Be+")."),we}else return"data"in P&&ot("WebGLRenderer: Image in DataTexture is too big ("+ge.width+"x"+ge.height+")."),P;return P}function _(P){return P.generateMipmaps}function v(P){s.generateMipmap(P)}function R(P){return P.isWebGLCubeRenderTarget?s.TEXTURE_CUBE_MAP:P.isWebGL3DRenderTarget?s.TEXTURE_3D:P.isWebGLArrayRenderTarget||P.isCompressedArrayTexture?s.TEXTURE_2D_ARRAY:s.TEXTURE_2D}function L(P,E,G,de,ge=!1){if(P!==null){if(s[P]!==void 0)return s[P];ot("WebGLRenderer: Attempt to use non-existing WebGL internal format '"+P+"'")}let ue=E;if(E===s.RED&&(G===s.FLOAT&&(ue=s.R32F),G===s.HALF_FLOAT&&(ue=s.R16F),G===s.UNSIGNED_BYTE&&(ue=s.R8)),E===s.RED_INTEGER&&(G===s.UNSIGNED_BYTE&&(ue=s.R8UI),G===s.UNSIGNED_SHORT&&(ue=s.R16UI),G===s.UNSIGNED_INT&&(ue=s.R32UI),G===s.BYTE&&(ue=s.R8I),G===s.SHORT&&(ue=s.R16I),G===s.INT&&(ue=s.R32I)),E===s.RG&&(G===s.FLOAT&&(ue=s.RG32F),G===s.HALF_FLOAT&&(ue=s.RG16F),G===s.UNSIGNED_BYTE&&(ue=s.RG8)),E===s.RG_INTEGER&&(G===s.UNSIGNED_BYTE&&(ue=s.RG8UI),G===s.UNSIGNED_SHORT&&(ue=s.RG16UI),G===s.UNSIGNED_INT&&(ue=s.RG32UI),G===s.BYTE&&(ue=s.RG8I),G===s.SHORT&&(ue=s.RG16I),G===s.INT&&(ue=s.RG32I)),E===s.RGB_INTEGER&&(G===s.UNSIGNED_BYTE&&(ue=s.RGB8UI),G===s.UNSIGNED_SHORT&&(ue=s.RGB16UI),G===s.UNSIGNED_INT&&(ue=s.RGB32UI),G===s.BYTE&&(ue=s.RGB8I),G===s.SHORT&&(ue=s.RGB16I),G===s.INT&&(ue=s.RGB32I)),E===s.RGBA_INTEGER&&(G===s.UNSIGNED_BYTE&&(ue=s.RGBA8UI),G===s.UNSIGNED_SHORT&&(ue=s.RGBA16UI),G===s.UNSIGNED_INT&&(ue=s.RGBA32UI),G===s.BYTE&&(ue=s.RGBA8I),G===s.SHORT&&(ue=s.RGBA16I),G===s.INT&&(ue=s.RGBA32I)),E===s.RGB&&(G===s.UNSIGNED_INT_5_9_9_9_REV&&(ue=s.RGB9_E5),G===s.UNSIGNED_INT_10F_11F_11F_REV&&(ue=s.R11F_G11F_B10F)),E===s.RGBA){const Be=ge?Nl:Et.getTransfer(de);G===s.FLOAT&&(ue=s.RGBA32F),G===s.HALF_FLOAT&&(ue=s.RGBA16F),G===s.UNSIGNED_BYTE&&(ue=Be===Dt?s.SRGB8_ALPHA8:s.RGBA8),G===s.UNSIGNED_SHORT_4_4_4_4&&(ue=s.RGBA4),G===s.UNSIGNED_SHORT_5_5_5_1&&(ue=s.RGB5_A1)}return(ue===s.R16F||ue===s.R32F||ue===s.RG16F||ue===s.RG32F||ue===s.RGBA16F||ue===s.RGBA32F)&&e.get("EXT_color_buffer_float"),ue}function b(P,E){let G;return P?E===null||E===Pi||E===Va?G=s.DEPTH24_STENCIL8:E===Ai?G=s.DEPTH32F_STENCIL8:E===za&&(G=s.DEPTH24_STENCIL8,ot("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):E===null||E===Pi||E===Va?G=s.DEPTH_COMPONENT24:E===Ai?G=s.DEPTH_COMPONENT32F:E===za&&(G=s.DEPTH_COMPONENT16),G}function F(P,E){return _(P)===!0||P.isFramebufferTexture&&P.minFilter!==cn&&P.minFilter!==_n?Math.log2(Math.max(E.width,E.height))+1:P.mipmaps!==void 0&&P.mipmaps.length>0?P.mipmaps.length:P.isCompressedTexture&&Array.isArray(P.image)?E.mipmaps.length:1}function U(P){const E=P.target;E.removeEventListener("dispose",U),A(E),E.isVideoTexture&&x.delete(E)}function z(P){const E=P.target;E.removeEventListener("dispose",z),fe(E)}function A(P){const E=r.get(P);if(E.__webglInit===void 0)return;const G=P.source,de=g.get(G);if(de){const ge=de[E.__cacheKey];ge.usedTimes--,ge.usedTimes===0&&D(P),Object.keys(de).length===0&&g.delete(G)}r.remove(P)}function D(P){const E=r.get(P);s.deleteTexture(E.__webglTexture);const G=P.source,de=g.get(G);delete de[E.__cacheKey],c.memory.textures--}function fe(P){const E=r.get(P);if(P.depthTexture&&(P.depthTexture.dispose(),r.remove(P.depthTexture)),P.isWebGLCubeRenderTarget)for(let de=0;de<6;de++){if(Array.isArray(E.__webglFramebuffer[de]))for(let ge=0;ge<E.__webglFramebuffer[de].length;ge++)s.deleteFramebuffer(E.__webglFramebuffer[de][ge]);else s.deleteFramebuffer(E.__webglFramebuffer[de]);E.__webglDepthbuffer&&s.deleteRenderbuffer(E.__webglDepthbuffer[de])}else{if(Array.isArray(E.__webglFramebuffer))for(let de=0;de<E.__webglFramebuffer.length;de++)s.deleteFramebuffer(E.__webglFramebuffer[de]);else s.deleteFramebuffer(E.__webglFramebuffer);if(E.__webglDepthbuffer&&s.deleteRenderbuffer(E.__webglDepthbuffer),E.__webglMultisampledFramebuffer&&s.deleteFramebuffer(E.__webglMultisampledFramebuffer),E.__webglColorRenderbuffer)for(let de=0;de<E.__webglColorRenderbuffer.length;de++)E.__webglColorRenderbuffer[de]&&s.deleteRenderbuffer(E.__webglColorRenderbuffer[de]);E.__webglDepthRenderbuffer&&s.deleteRenderbuffer(E.__webglDepthRenderbuffer)}const G=P.textures;for(let de=0,ge=G.length;de<ge;de++){const ue=r.get(G[de]);ue.__webglTexture&&(s.deleteTexture(ue.__webglTexture),c.memory.textures--),r.remove(G[de])}r.remove(P)}let O=0;function te(){O=0}function Q(){const P=O;return P>=o.maxTextures&&ot("WebGLTextures: Trying to use "+P+" texture units while this GPU supports only "+o.maxTextures),O+=1,P}function oe(P){const E=[];return E.push(P.wrapS),E.push(P.wrapT),E.push(P.wrapR||0),E.push(P.magFilter),E.push(P.minFilter),E.push(P.anisotropy),E.push(P.internalFormat),E.push(P.format),E.push(P.type),E.push(P.generateMipmaps),E.push(P.premultiplyAlpha),E.push(P.flipY),E.push(P.unpackAlignment),E.push(P.colorSpace),E.join()}function K(P,E){const G=r.get(P);if(P.isVideoTexture&&mt(P),P.isRenderTargetTexture===!1&&P.isExternalTexture!==!0&&P.version>0&&G.__version!==P.version){const de=P.image;if(de===null)ot("WebGLRenderer: Texture marked for update but no image data found.");else if(de.complete===!1)ot("WebGLRenderer: Texture marked for update but image is incomplete");else{ie(G,P,E);return}}else P.isExternalTexture&&(G.__webglTexture=P.sourceTexture?P.sourceTexture:null);n.bindTexture(s.TEXTURE_2D,G.__webglTexture,s.TEXTURE0+E)}function ee(P,E){const G=r.get(P);if(P.isRenderTargetTexture===!1&&P.version>0&&G.__version!==P.version){ie(G,P,E);return}else P.isExternalTexture&&(G.__webglTexture=P.sourceTexture?P.sourceTexture:null);n.bindTexture(s.TEXTURE_2D_ARRAY,G.__webglTexture,s.TEXTURE0+E)}function W(P,E){const G=r.get(P);if(P.isRenderTargetTexture===!1&&P.version>0&&G.__version!==P.version){ie(G,P,E);return}n.bindTexture(s.TEXTURE_3D,G.__webglTexture,s.TEXTURE0+E)}function q(P,E){const G=r.get(P);if(P.isCubeDepthTexture!==!0&&P.version>0&&G.__version!==P.version){me(G,P,E);return}n.bindTexture(s.TEXTURE_CUBE_MAP,G.__webglTexture,s.TEXTURE0+E)}const ae={[mf]:s.REPEAT,[Yi]:s.CLAMP_TO_EDGE,[gf]:s.MIRRORED_REPEAT},le={[cn]:s.NEAREST,[P0]:s.NEAREST_MIPMAP_NEAREST,[nl]:s.NEAREST_MIPMAP_LINEAR,[_n]:s.LINEAR,[Rc]:s.LINEAR_MIPMAP_NEAREST,[Jr]:s.LINEAR_MIPMAP_LINEAR},I={[I0]:s.NEVER,[k0]:s.ALWAYS,[U0]:s.LESS,[od]:s.LEQUAL,[F0]:s.EQUAL,[ld]:s.GEQUAL,[O0]:s.GREATER,[B0]:s.NOTEQUAL};function j(P,E){if(E.type===Ai&&e.has("OES_texture_float_linear")===!1&&(E.magFilter===_n||E.magFilter===Rc||E.magFilter===nl||E.magFilter===Jr||E.minFilter===_n||E.minFilter===Rc||E.minFilter===nl||E.minFilter===Jr)&&ot("WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),s.texParameteri(P,s.TEXTURE_WRAP_S,ae[E.wrapS]),s.texParameteri(P,s.TEXTURE_WRAP_T,ae[E.wrapT]),(P===s.TEXTURE_3D||P===s.TEXTURE_2D_ARRAY)&&s.texParameteri(P,s.TEXTURE_WRAP_R,ae[E.wrapR]),s.texParameteri(P,s.TEXTURE_MAG_FILTER,le[E.magFilter]),s.texParameteri(P,s.TEXTURE_MIN_FILTER,le[E.minFilter]),E.compareFunction&&(s.texParameteri(P,s.TEXTURE_COMPARE_MODE,s.COMPARE_REF_TO_TEXTURE),s.texParameteri(P,s.TEXTURE_COMPARE_FUNC,I[E.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){if(E.magFilter===cn||E.minFilter!==nl&&E.minFilter!==Jr||E.type===Ai&&e.has("OES_texture_float_linear")===!1)return;if(E.anisotropy>1||r.get(E).__currentAnisotropy){const G=e.get("EXT_texture_filter_anisotropic");s.texParameterf(P,G.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(E.anisotropy,o.getMaxAnisotropy())),r.get(E).__currentAnisotropy=E.anisotropy}}}function Ce(P,E){let G=!1;P.__webglInit===void 0&&(P.__webglInit=!0,E.addEventListener("dispose",U));const de=E.source;let ge=g.get(de);ge===void 0&&(ge={},g.set(de,ge));const ue=oe(E);if(ue!==P.__cacheKey){ge[ue]===void 0&&(ge[ue]={texture:s.createTexture(),usedTimes:0},c.memory.textures++,G=!0),ge[ue].usedTimes++;const Be=ge[P.__cacheKey];Be!==void 0&&(ge[P.__cacheKey].usedTimes--,Be.usedTimes===0&&D(E)),P.__cacheKey=ue,P.__webglTexture=ge[ue].texture}return G}function Xe(P,E,G){return Math.floor(Math.floor(P/G)/E)}function Ze(P,E,G,de){const ue=P.updateRanges;if(ue.length===0)n.texSubImage2D(s.TEXTURE_2D,0,0,0,E.width,E.height,G,de,E.data);else{ue.sort((Se,Te)=>Se.start-Te.start);let Be=0;for(let Se=1;Se<ue.length;Se++){const Te=ue[Be],We=ue[Se],ke=Te.start+Te.count,De=Xe(We.start,E.width,4),lt=Xe(Te.start,E.width,4);We.start<=ke+1&&De===lt&&Xe(We.start+We.count-1,E.width,4)===De?Te.count=Math.max(Te.count,We.start+We.count-Te.start):(++Be,ue[Be]=We)}ue.length=Be+1;const we=s.getParameter(s.UNPACK_ROW_LENGTH),qe=s.getParameter(s.UNPACK_SKIP_PIXELS),it=s.getParameter(s.UNPACK_SKIP_ROWS);s.pixelStorei(s.UNPACK_ROW_LENGTH,E.width);for(let Se=0,Te=ue.length;Se<Te;Se++){const We=ue[Se],ke=Math.floor(We.start/4),De=Math.ceil(We.count/4),lt=ke%E.width,V=Math.floor(ke/E.width),Ae=De,Me=1;s.pixelStorei(s.UNPACK_SKIP_PIXELS,lt),s.pixelStorei(s.UNPACK_SKIP_ROWS,V),n.texSubImage2D(s.TEXTURE_2D,0,lt,V,Ae,Me,G,de,E.data)}P.clearUpdateRanges(),s.pixelStorei(s.UNPACK_ROW_LENGTH,we),s.pixelStorei(s.UNPACK_SKIP_PIXELS,qe),s.pixelStorei(s.UNPACK_SKIP_ROWS,it)}}function ie(P,E,G){let de=s.TEXTURE_2D;(E.isDataArrayTexture||E.isCompressedArrayTexture)&&(de=s.TEXTURE_2D_ARRAY),E.isData3DTexture&&(de=s.TEXTURE_3D);const ge=Ce(P,E),ue=E.source;n.bindTexture(de,P.__webglTexture,s.TEXTURE0+G);const Be=r.get(ue);if(ue.version!==Be.__version||ge===!0){n.activeTexture(s.TEXTURE0+G);const we=Et.getPrimaries(Et.workingColorSpace),qe=E.colorSpace===Ar?null:Et.getPrimaries(E.colorSpace),it=E.colorSpace===Ar||we===qe?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,E.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,E.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,E.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,it);let Se=C(E.image,!1,o.maxTextureSize);Se=St(E,Se);const Te=u.convert(E.format,E.colorSpace),We=u.convert(E.type);let ke=L(E.internalFormat,Te,We,E.colorSpace,E.isVideoTexture);j(de,E);let De;const lt=E.mipmaps,V=E.isVideoTexture!==!0,Ae=Be.__version===void 0||ge===!0,Me=ue.dataReady,Le=F(E,Se);if(E.isDepthTexture)ke=b(E.format===es,E.type),Ae&&(V?n.texStorage2D(s.TEXTURE_2D,1,ke,Se.width,Se.height):n.texImage2D(s.TEXTURE_2D,0,ke,Se.width,Se.height,0,Te,We,null));else if(E.isDataTexture)if(lt.length>0){V&&Ae&&n.texStorage2D(s.TEXTURE_2D,Le,ke,lt[0].width,lt[0].height);for(let ye=0,ce=lt.length;ye<ce;ye++)De=lt[ye],V?Me&&n.texSubImage2D(s.TEXTURE_2D,ye,0,0,De.width,De.height,Te,We,De.data):n.texImage2D(s.TEXTURE_2D,ye,ke,De.width,De.height,0,Te,We,De.data);E.generateMipmaps=!1}else V?(Ae&&n.texStorage2D(s.TEXTURE_2D,Le,ke,Se.width,Se.height),Me&&Ze(E,Se,Te,We)):n.texImage2D(s.TEXTURE_2D,0,ke,Se.width,Se.height,0,Te,We,Se.data);else if(E.isCompressedTexture)if(E.isCompressedArrayTexture){V&&Ae&&n.texStorage3D(s.TEXTURE_2D_ARRAY,Le,ke,lt[0].width,lt[0].height,Se.depth);for(let ye=0,ce=lt.length;ye<ce;ye++)if(De=lt[ye],E.format!==mi)if(Te!==null)if(V){if(Me)if(E.layerUpdates.size>0){const ze=fm(De.width,De.height,E.format,E.type);for(const rt of E.layerUpdates){const Pt=De.data.subarray(rt*ze/De.data.BYTES_PER_ELEMENT,(rt+1)*ze/De.data.BYTES_PER_ELEMENT);n.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,ye,0,0,rt,De.width,De.height,1,Te,Pt)}E.clearLayerUpdates()}else n.compressedTexSubImage3D(s.TEXTURE_2D_ARRAY,ye,0,0,0,De.width,De.height,Se.depth,Te,De.data)}else n.compressedTexImage3D(s.TEXTURE_2D_ARRAY,ye,ke,De.width,De.height,Se.depth,0,De.data,0,0);else ot("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else V?Me&&n.texSubImage3D(s.TEXTURE_2D_ARRAY,ye,0,0,0,De.width,De.height,Se.depth,Te,We,De.data):n.texImage3D(s.TEXTURE_2D_ARRAY,ye,ke,De.width,De.height,Se.depth,0,Te,We,De.data)}else{V&&Ae&&n.texStorage2D(s.TEXTURE_2D,Le,ke,lt[0].width,lt[0].height);for(let ye=0,ce=lt.length;ye<ce;ye++)De=lt[ye],E.format!==mi?Te!==null?V?Me&&n.compressedTexSubImage2D(s.TEXTURE_2D,ye,0,0,De.width,De.height,Te,De.data):n.compressedTexImage2D(s.TEXTURE_2D,ye,ke,De.width,De.height,0,De.data):ot("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):V?Me&&n.texSubImage2D(s.TEXTURE_2D,ye,0,0,De.width,De.height,Te,We,De.data):n.texImage2D(s.TEXTURE_2D,ye,ke,De.width,De.height,0,Te,We,De.data)}else if(E.isDataArrayTexture)if(V){if(Ae&&n.texStorage3D(s.TEXTURE_2D_ARRAY,Le,ke,Se.width,Se.height,Se.depth),Me)if(E.layerUpdates.size>0){const ye=fm(Se.width,Se.height,E.format,E.type);for(const ce of E.layerUpdates){const ze=Se.data.subarray(ce*ye/Se.data.BYTES_PER_ELEMENT,(ce+1)*ye/Se.data.BYTES_PER_ELEMENT);n.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,ce,Se.width,Se.height,1,Te,We,ze)}E.clearLayerUpdates()}else n.texSubImage3D(s.TEXTURE_2D_ARRAY,0,0,0,0,Se.width,Se.height,Se.depth,Te,We,Se.data)}else n.texImage3D(s.TEXTURE_2D_ARRAY,0,ke,Se.width,Se.height,Se.depth,0,Te,We,Se.data);else if(E.isData3DTexture)V?(Ae&&n.texStorage3D(s.TEXTURE_3D,Le,ke,Se.width,Se.height,Se.depth),Me&&n.texSubImage3D(s.TEXTURE_3D,0,0,0,0,Se.width,Se.height,Se.depth,Te,We,Se.data)):n.texImage3D(s.TEXTURE_3D,0,ke,Se.width,Se.height,Se.depth,0,Te,We,Se.data);else if(E.isFramebufferTexture){if(Ae)if(V)n.texStorage2D(s.TEXTURE_2D,Le,ke,Se.width,Se.height);else{let ye=Se.width,ce=Se.height;for(let ze=0;ze<Le;ze++)n.texImage2D(s.TEXTURE_2D,ze,ke,ye,ce,0,Te,We,null),ye>>=1,ce>>=1}}else if(lt.length>0){if(V&&Ae){const ye=Ge(lt[0]);n.texStorage2D(s.TEXTURE_2D,Le,ke,ye.width,ye.height)}for(let ye=0,ce=lt.length;ye<ce;ye++)De=lt[ye],V?Me&&n.texSubImage2D(s.TEXTURE_2D,ye,0,0,Te,We,De):n.texImage2D(s.TEXTURE_2D,ye,ke,Te,We,De);E.generateMipmaps=!1}else if(V){if(Ae){const ye=Ge(Se);n.texStorage2D(s.TEXTURE_2D,Le,ke,ye.width,ye.height)}Me&&n.texSubImage2D(s.TEXTURE_2D,0,0,0,Te,We,Se)}else n.texImage2D(s.TEXTURE_2D,0,ke,Te,We,Se);_(E)&&v(de),Be.__version=ue.version,E.onUpdate&&E.onUpdate(E)}P.__version=E.version}function me(P,E,G){if(E.image.length!==6)return;const de=Ce(P,E),ge=E.source;n.bindTexture(s.TEXTURE_CUBE_MAP,P.__webglTexture,s.TEXTURE0+G);const ue=r.get(ge);if(ge.version!==ue.__version||de===!0){n.activeTexture(s.TEXTURE0+G);const Be=Et.getPrimaries(Et.workingColorSpace),we=E.colorSpace===Ar?null:Et.getPrimaries(E.colorSpace),qe=E.colorSpace===Ar||Be===we?s.NONE:s.BROWSER_DEFAULT_WEBGL;s.pixelStorei(s.UNPACK_FLIP_Y_WEBGL,E.flipY),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,E.premultiplyAlpha),s.pixelStorei(s.UNPACK_ALIGNMENT,E.unpackAlignment),s.pixelStorei(s.UNPACK_COLORSPACE_CONVERSION_WEBGL,qe);const it=E.isCompressedTexture||E.image[0].isCompressedTexture,Se=E.image[0]&&E.image[0].isDataTexture,Te=[];for(let ce=0;ce<6;ce++)!it&&!Se?Te[ce]=C(E.image[ce],!0,o.maxCubemapSize):Te[ce]=Se?E.image[ce].image:E.image[ce],Te[ce]=St(E,Te[ce]);const We=Te[0],ke=u.convert(E.format,E.colorSpace),De=u.convert(E.type),lt=L(E.internalFormat,ke,De,E.colorSpace),V=E.isVideoTexture!==!0,Ae=ue.__version===void 0||de===!0,Me=ge.dataReady;let Le=F(E,We);j(s.TEXTURE_CUBE_MAP,E);let ye;if(it){V&&Ae&&n.texStorage2D(s.TEXTURE_CUBE_MAP,Le,lt,We.width,We.height);for(let ce=0;ce<6;ce++){ye=Te[ce].mipmaps;for(let ze=0;ze<ye.length;ze++){const rt=ye[ze];E.format!==mi?ke!==null?V?Me&&n.compressedTexSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze,0,0,rt.width,rt.height,ke,rt.data):n.compressedTexImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze,lt,rt.width,rt.height,0,rt.data):ot("WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):V?Me&&n.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze,0,0,rt.width,rt.height,ke,De,rt.data):n.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze,lt,rt.width,rt.height,0,ke,De,rt.data)}}}else{if(ye=E.mipmaps,V&&Ae){ye.length>0&&Le++;const ce=Ge(Te[0]);n.texStorage2D(s.TEXTURE_CUBE_MAP,Le,lt,ce.width,ce.height)}for(let ce=0;ce<6;ce++)if(Se){V?Me&&n.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,0,0,0,Te[ce].width,Te[ce].height,ke,De,Te[ce].data):n.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,0,lt,Te[ce].width,Te[ce].height,0,ke,De,Te[ce].data);for(let ze=0;ze<ye.length;ze++){const Pt=ye[ze].image[ce].image;V?Me&&n.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze+1,0,0,Pt.width,Pt.height,ke,De,Pt.data):n.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze+1,lt,Pt.width,Pt.height,0,ke,De,Pt.data)}}else{V?Me&&n.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,0,0,0,ke,De,Te[ce]):n.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,0,lt,ke,De,Te[ce]);for(let ze=0;ze<ye.length;ze++){const rt=ye[ze];V?Me&&n.texSubImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze+1,0,0,ke,De,rt.image[ce]):n.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+ce,ze+1,lt,ke,De,rt.image[ce])}}}_(E)&&v(s.TEXTURE_CUBE_MAP),ue.__version=ge.version,E.onUpdate&&E.onUpdate(E)}P.__version=E.version}function pe(P,E,G,de,ge,ue){const Be=u.convert(G.format,G.colorSpace),we=u.convert(G.type),qe=L(G.internalFormat,Be,we,G.colorSpace),it=r.get(E),Se=r.get(G);if(Se.__renderTarget=E,!it.__hasExternalTextures){const Te=Math.max(1,E.width>>ue),We=Math.max(1,E.height>>ue);ge===s.TEXTURE_3D||ge===s.TEXTURE_2D_ARRAY?n.texImage3D(ge,ue,qe,Te,We,E.depth,0,Be,we,null):n.texImage2D(ge,ue,qe,Te,We,0,Be,we,null)}n.bindFramebuffer(s.FRAMEBUFFER,P),kt(E)?d.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,de,ge,Se.__webglTexture,0,k(E)):(ge===s.TEXTURE_2D||ge>=s.TEXTURE_CUBE_MAP_POSITIVE_X&&ge<=s.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&s.framebufferTexture2D(s.FRAMEBUFFER,de,ge,Se.__webglTexture,ue),n.bindFramebuffer(s.FRAMEBUFFER,null)}function Fe(P,E,G){if(s.bindRenderbuffer(s.RENDERBUFFER,P),E.depthBuffer){const de=E.depthTexture,ge=de&&de.isDepthTexture?de.type:null,ue=b(E.stencilBuffer,ge),Be=E.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;kt(E)?d.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,k(E),ue,E.width,E.height):G?s.renderbufferStorageMultisample(s.RENDERBUFFER,k(E),ue,E.width,E.height):s.renderbufferStorage(s.RENDERBUFFER,ue,E.width,E.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,Be,s.RENDERBUFFER,P)}else{const de=E.textures;for(let ge=0;ge<de.length;ge++){const ue=de[ge],Be=u.convert(ue.format,ue.colorSpace),we=u.convert(ue.type),qe=L(ue.internalFormat,Be,we,ue.colorSpace);kt(E)?d.renderbufferStorageMultisampleEXT(s.RENDERBUFFER,k(E),qe,E.width,E.height):G?s.renderbufferStorageMultisample(s.RENDERBUFFER,k(E),qe,E.width,E.height):s.renderbufferStorage(s.RENDERBUFFER,qe,E.width,E.height)}}s.bindRenderbuffer(s.RENDERBUFFER,null)}function He(P,E,G){const de=E.isWebGLCubeRenderTarget===!0;if(n.bindFramebuffer(s.FRAMEBUFFER,P),!(E.depthTexture&&E.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");const ge=r.get(E.depthTexture);if(ge.__renderTarget=E,(!ge.__webglTexture||E.depthTexture.image.width!==E.width||E.depthTexture.image.height!==E.height)&&(E.depthTexture.image.width=E.width,E.depthTexture.image.height=E.height,E.depthTexture.needsUpdate=!0),de){if(ge.__webglInit===void 0&&(ge.__webglInit=!0,E.depthTexture.addEventListener("dispose",U)),ge.__webglTexture===void 0){ge.__webglTexture=s.createTexture(),n.bindTexture(s.TEXTURE_CUBE_MAP,ge.__webglTexture),j(s.TEXTURE_CUBE_MAP,E.depthTexture);const it=u.convert(E.depthTexture.format),Se=u.convert(E.depthTexture.type);let Te;E.depthTexture.format===Zi?Te=s.DEPTH_COMPONENT24:E.depthTexture.format===es&&(Te=s.DEPTH24_STENCIL8);for(let We=0;We<6;We++)s.texImage2D(s.TEXTURE_CUBE_MAP_POSITIVE_X+We,0,Te,E.width,E.height,0,it,Se,null)}}else K(E.depthTexture,0);const ue=ge.__webglTexture,Be=k(E),we=de?s.TEXTURE_CUBE_MAP_POSITIVE_X+G:s.TEXTURE_2D,qe=E.depthTexture.format===es?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;if(E.depthTexture.format===Zi)kt(E)?d.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,qe,we,ue,0,Be):s.framebufferTexture2D(s.FRAMEBUFFER,qe,we,ue,0);else if(E.depthTexture.format===es)kt(E)?d.framebufferTexture2DMultisampleEXT(s.FRAMEBUFFER,qe,we,ue,0,Be):s.framebufferTexture2D(s.FRAMEBUFFER,qe,we,ue,0);else throw new Error("Unknown depthTexture format")}function nt(P){const E=r.get(P),G=P.isWebGLCubeRenderTarget===!0;if(E.__boundDepthTexture!==P.depthTexture){const de=P.depthTexture;if(E.__depthDisposeCallback&&E.__depthDisposeCallback(),de){const ge=()=>{delete E.__boundDepthTexture,delete E.__depthDisposeCallback,de.removeEventListener("dispose",ge)};de.addEventListener("dispose",ge),E.__depthDisposeCallback=ge}E.__boundDepthTexture=de}if(P.depthTexture&&!E.__autoAllocateDepthBuffer)if(G)for(let de=0;de<6;de++)He(E.__webglFramebuffer[de],P,de);else{const de=P.texture.mipmaps;de&&de.length>0?He(E.__webglFramebuffer[0],P,0):He(E.__webglFramebuffer,P,0)}else if(G){E.__webglDepthbuffer=[];for(let de=0;de<6;de++)if(n.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer[de]),E.__webglDepthbuffer[de]===void 0)E.__webglDepthbuffer[de]=s.createRenderbuffer(),Fe(E.__webglDepthbuffer[de],P,!1);else{const ge=P.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,ue=E.__webglDepthbuffer[de];s.bindRenderbuffer(s.RENDERBUFFER,ue),s.framebufferRenderbuffer(s.FRAMEBUFFER,ge,s.RENDERBUFFER,ue)}}else{const de=P.texture.mipmaps;if(de&&de.length>0?n.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer[0]):n.bindFramebuffer(s.FRAMEBUFFER,E.__webglFramebuffer),E.__webglDepthbuffer===void 0)E.__webglDepthbuffer=s.createRenderbuffer(),Fe(E.__webglDepthbuffer,P,!1);else{const ge=P.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,ue=E.__webglDepthbuffer;s.bindRenderbuffer(s.RENDERBUFFER,ue),s.framebufferRenderbuffer(s.FRAMEBUFFER,ge,s.RENDERBUFFER,ue)}}n.bindFramebuffer(s.FRAMEBUFFER,null)}function Wt(P,E,G){const de=r.get(P);E!==void 0&&pe(de.__webglFramebuffer,P,P.texture,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,0),G!==void 0&&nt(P)}function ht(P){const E=P.texture,G=r.get(P),de=r.get(E);P.addEventListener("dispose",z);const ge=P.textures,ue=P.isWebGLCubeRenderTarget===!0,Be=ge.length>1;if(Be||(de.__webglTexture===void 0&&(de.__webglTexture=s.createTexture()),de.__version=E.version,c.memory.textures++),ue){G.__webglFramebuffer=[];for(let we=0;we<6;we++)if(E.mipmaps&&E.mipmaps.length>0){G.__webglFramebuffer[we]=[];for(let qe=0;qe<E.mipmaps.length;qe++)G.__webglFramebuffer[we][qe]=s.createFramebuffer()}else G.__webglFramebuffer[we]=s.createFramebuffer()}else{if(E.mipmaps&&E.mipmaps.length>0){G.__webglFramebuffer=[];for(let we=0;we<E.mipmaps.length;we++)G.__webglFramebuffer[we]=s.createFramebuffer()}else G.__webglFramebuffer=s.createFramebuffer();if(Be)for(let we=0,qe=ge.length;we<qe;we++){const it=r.get(ge[we]);it.__webglTexture===void 0&&(it.__webglTexture=s.createTexture(),c.memory.textures++)}if(P.samples>0&&kt(P)===!1){G.__webglMultisampledFramebuffer=s.createFramebuffer(),G.__webglColorRenderbuffer=[],n.bindFramebuffer(s.FRAMEBUFFER,G.__webglMultisampledFramebuffer);for(let we=0;we<ge.length;we++){const qe=ge[we];G.__webglColorRenderbuffer[we]=s.createRenderbuffer(),s.bindRenderbuffer(s.RENDERBUFFER,G.__webglColorRenderbuffer[we]);const it=u.convert(qe.format,qe.colorSpace),Se=u.convert(qe.type),Te=L(qe.internalFormat,it,Se,qe.colorSpace,P.isXRRenderTarget===!0),We=k(P);s.renderbufferStorageMultisample(s.RENDERBUFFER,We,Te,P.width,P.height),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+we,s.RENDERBUFFER,G.__webglColorRenderbuffer[we])}s.bindRenderbuffer(s.RENDERBUFFER,null),P.depthBuffer&&(G.__webglDepthRenderbuffer=s.createRenderbuffer(),Fe(G.__webglDepthRenderbuffer,P,!0)),n.bindFramebuffer(s.FRAMEBUFFER,null)}}if(ue){n.bindTexture(s.TEXTURE_CUBE_MAP,de.__webglTexture),j(s.TEXTURE_CUBE_MAP,E);for(let we=0;we<6;we++)if(E.mipmaps&&E.mipmaps.length>0)for(let qe=0;qe<E.mipmaps.length;qe++)pe(G.__webglFramebuffer[we][qe],P,E,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+we,qe);else pe(G.__webglFramebuffer[we],P,E,s.COLOR_ATTACHMENT0,s.TEXTURE_CUBE_MAP_POSITIVE_X+we,0);_(E)&&v(s.TEXTURE_CUBE_MAP),n.unbindTexture()}else if(Be){for(let we=0,qe=ge.length;we<qe;we++){const it=ge[we],Se=r.get(it);let Te=s.TEXTURE_2D;(P.isWebGL3DRenderTarget||P.isWebGLArrayRenderTarget)&&(Te=P.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),n.bindTexture(Te,Se.__webglTexture),j(Te,it),pe(G.__webglFramebuffer,P,it,s.COLOR_ATTACHMENT0+we,Te,0),_(it)&&v(Te)}n.unbindTexture()}else{let we=s.TEXTURE_2D;if((P.isWebGL3DRenderTarget||P.isWebGLArrayRenderTarget)&&(we=P.isWebGL3DRenderTarget?s.TEXTURE_3D:s.TEXTURE_2D_ARRAY),n.bindTexture(we,de.__webglTexture),j(we,E),E.mipmaps&&E.mipmaps.length>0)for(let qe=0;qe<E.mipmaps.length;qe++)pe(G.__webglFramebuffer[qe],P,E,s.COLOR_ATTACHMENT0,we,qe);else pe(G.__webglFramebuffer,P,E,s.COLOR_ATTACHMENT0,we,0);_(E)&&v(we),n.unbindTexture()}P.depthBuffer&&nt(P)}function xt(P){const E=P.textures;for(let G=0,de=E.length;G<de;G++){const ge=E[G];if(_(ge)){const ue=R(P),Be=r.get(ge).__webglTexture;n.bindTexture(ue,Be),v(ue),n.unbindTexture()}}}const Ct=[],ut=[];function Ft(P){if(P.samples>0){if(kt(P)===!1){const E=P.textures,G=P.width,de=P.height;let ge=s.COLOR_BUFFER_BIT;const ue=P.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT,Be=r.get(P),we=E.length>1;if(we)for(let it=0;it<E.length;it++)n.bindFramebuffer(s.FRAMEBUFFER,Be.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+it,s.RENDERBUFFER,null),n.bindFramebuffer(s.FRAMEBUFFER,Be.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+it,s.TEXTURE_2D,null,0);n.bindFramebuffer(s.READ_FRAMEBUFFER,Be.__webglMultisampledFramebuffer);const qe=P.texture.mipmaps;qe&&qe.length>0?n.bindFramebuffer(s.DRAW_FRAMEBUFFER,Be.__webglFramebuffer[0]):n.bindFramebuffer(s.DRAW_FRAMEBUFFER,Be.__webglFramebuffer);for(let it=0;it<E.length;it++){if(P.resolveDepthBuffer&&(P.depthBuffer&&(ge|=s.DEPTH_BUFFER_BIT),P.stencilBuffer&&P.resolveStencilBuffer&&(ge|=s.STENCIL_BUFFER_BIT)),we){s.framebufferRenderbuffer(s.READ_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.RENDERBUFFER,Be.__webglColorRenderbuffer[it]);const Se=r.get(E[it]).__webglTexture;s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0,s.TEXTURE_2D,Se,0)}s.blitFramebuffer(0,0,G,de,0,0,G,de,ge,s.NEAREST),p===!0&&(Ct.length=0,ut.length=0,Ct.push(s.COLOR_ATTACHMENT0+it),P.depthBuffer&&P.resolveDepthBuffer===!1&&(Ct.push(ue),ut.push(ue),s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,ut)),s.invalidateFramebuffer(s.READ_FRAMEBUFFER,Ct))}if(n.bindFramebuffer(s.READ_FRAMEBUFFER,null),n.bindFramebuffer(s.DRAW_FRAMEBUFFER,null),we)for(let it=0;it<E.length;it++){n.bindFramebuffer(s.FRAMEBUFFER,Be.__webglMultisampledFramebuffer),s.framebufferRenderbuffer(s.FRAMEBUFFER,s.COLOR_ATTACHMENT0+it,s.RENDERBUFFER,Be.__webglColorRenderbuffer[it]);const Se=r.get(E[it]).__webglTexture;n.bindFramebuffer(s.FRAMEBUFFER,Be.__webglFramebuffer),s.framebufferTexture2D(s.DRAW_FRAMEBUFFER,s.COLOR_ATTACHMENT0+it,s.TEXTURE_2D,Se,0)}n.bindFramebuffer(s.DRAW_FRAMEBUFFER,Be.__webglMultisampledFramebuffer)}else if(P.depthBuffer&&P.resolveDepthBuffer===!1&&p){const E=P.stencilBuffer?s.DEPTH_STENCIL_ATTACHMENT:s.DEPTH_ATTACHMENT;s.invalidateFramebuffer(s.DRAW_FRAMEBUFFER,[E])}}}function k(P){return Math.min(o.maxSamples,P.samples)}function kt(P){const E=r.get(P);return P.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&E.__useRenderToTexture!==!1}function mt(P){const E=c.render.frame;x.get(P)!==E&&(x.set(P,E),P.update())}function St(P,E){const G=P.colorSpace,de=P.format,ge=P.type;return P.isCompressedTexture===!0||P.isVideoTexture===!0||G!==Xs&&G!==Ar&&(Et.getTransfer(G)===Dt?(de!==mi||ge!==ni)&&ot("WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):wt("WebGLTextures: Unsupported texture color space:",G)),E}function Ge(P){return typeof HTMLImageElement<"u"&&P instanceof HTMLImageElement?(m.width=P.naturalWidth||P.width,m.height=P.naturalHeight||P.height):typeof VideoFrame<"u"&&P instanceof VideoFrame?(m.width=P.displayWidth,m.height=P.displayHeight):(m.width=P.width,m.height=P.height),m}this.allocateTextureUnit=Q,this.resetTextureUnits=te,this.setTexture2D=K,this.setTexture2DArray=ee,this.setTexture3D=W,this.setTextureCube=q,this.rebindTextures=Wt,this.setupRenderTarget=ht,this.updateRenderTargetMipmap=xt,this.updateMultisampleRenderTarget=Ft,this.setupDepthRenderbuffer=nt,this.setupFrameBufferTexture=pe,this.useMultisampledRTT=kt,this.isReversedDepthBuffer=function(){return n.buffers.depth.getReversed()}}function lE(s,e){function n(r,o=Ar){let u;const c=Et.getTransfer(o);if(r===ni)return s.UNSIGNED_BYTE;if(r===nd)return s.UNSIGNED_SHORT_4_4_4_4;if(r===id)return s.UNSIGNED_SHORT_5_5_5_1;if(r===Ym)return s.UNSIGNED_INT_5_9_9_9_REV;if(r===qm)return s.UNSIGNED_INT_10F_11F_11F_REV;if(r===Xm)return s.BYTE;if(r===jm)return s.SHORT;if(r===za)return s.UNSIGNED_SHORT;if(r===td)return s.INT;if(r===Pi)return s.UNSIGNED_INT;if(r===Ai)return s.FLOAT;if(r===Ki)return s.HALF_FLOAT;if(r===$m)return s.ALPHA;if(r===Km)return s.RGB;if(r===mi)return s.RGBA;if(r===Zi)return s.DEPTH_COMPONENT;if(r===es)return s.DEPTH_STENCIL;if(r===Zm)return s.RED;if(r===rd)return s.RED_INTEGER;if(r===Ws)return s.RG;if(r===sd)return s.RG_INTEGER;if(r===ad)return s.RGBA_INTEGER;if(r===Rl||r===bl||r===Pl||r===Dl)if(c===Dt)if(u=e.get("WEBGL_compressed_texture_s3tc_srgb"),u!==null){if(r===Rl)return u.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(r===bl)return u.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(r===Pl)return u.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(r===Dl)return u.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(u=e.get("WEBGL_compressed_texture_s3tc"),u!==null){if(r===Rl)return u.COMPRESSED_RGB_S3TC_DXT1_EXT;if(r===bl)return u.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(r===Pl)return u.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(r===Dl)return u.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(r===_f||r===vf||r===xf||r===Sf)if(u=e.get("WEBGL_compressed_texture_pvrtc"),u!==null){if(r===_f)return u.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(r===vf)return u.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(r===xf)return u.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(r===Sf)return u.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(r===yf||r===Mf||r===Ef||r===Tf||r===wf||r===Af||r===Cf)if(u=e.get("WEBGL_compressed_texture_etc"),u!==null){if(r===yf||r===Mf)return c===Dt?u.COMPRESSED_SRGB8_ETC2:u.COMPRESSED_RGB8_ETC2;if(r===Ef)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:u.COMPRESSED_RGBA8_ETC2_EAC;if(r===Tf)return u.COMPRESSED_R11_EAC;if(r===wf)return u.COMPRESSED_SIGNED_R11_EAC;if(r===Af)return u.COMPRESSED_RG11_EAC;if(r===Cf)return u.COMPRESSED_SIGNED_RG11_EAC}else return null;if(r===Rf||r===bf||r===Pf||r===Df||r===Lf||r===Nf||r===If||r===Uf||r===Ff||r===Of||r===Bf||r===kf||r===zf||r===Vf)if(u=e.get("WEBGL_compressed_texture_astc"),u!==null){if(r===Rf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:u.COMPRESSED_RGBA_ASTC_4x4_KHR;if(r===bf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:u.COMPRESSED_RGBA_ASTC_5x4_KHR;if(r===Pf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:u.COMPRESSED_RGBA_ASTC_5x5_KHR;if(r===Df)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:u.COMPRESSED_RGBA_ASTC_6x5_KHR;if(r===Lf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:u.COMPRESSED_RGBA_ASTC_6x6_KHR;if(r===Nf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:u.COMPRESSED_RGBA_ASTC_8x5_KHR;if(r===If)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:u.COMPRESSED_RGBA_ASTC_8x6_KHR;if(r===Uf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:u.COMPRESSED_RGBA_ASTC_8x8_KHR;if(r===Ff)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:u.COMPRESSED_RGBA_ASTC_10x5_KHR;if(r===Of)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:u.COMPRESSED_RGBA_ASTC_10x6_KHR;if(r===Bf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:u.COMPRESSED_RGBA_ASTC_10x8_KHR;if(r===kf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:u.COMPRESSED_RGBA_ASTC_10x10_KHR;if(r===zf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:u.COMPRESSED_RGBA_ASTC_12x10_KHR;if(r===Vf)return c===Dt?u.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:u.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(r===Hf||r===Gf||r===Wf)if(u=e.get("EXT_texture_compression_bptc"),u!==null){if(r===Hf)return c===Dt?u.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:u.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(r===Gf)return u.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(r===Wf)return u.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(r===Xf||r===jf||r===Yf||r===qf)if(u=e.get("EXT_texture_compression_rgtc"),u!==null){if(r===Xf)return u.COMPRESSED_RED_RGTC1_EXT;if(r===jf)return u.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(r===Yf)return u.COMPRESSED_RED_GREEN_RGTC2_EXT;if(r===qf)return u.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return r===Va?s.UNSIGNED_INT_24_8:s[r]!==void 0?s[r]:null}return{convert:n}}const uE=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,cE=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;class fE{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,n){if(this.texture===null){const r=new lg(e.texture);(e.depthNear!==n.depthNear||e.depthFar!==n.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=r}}getMesh(e){if(this.texture!==null&&this.mesh===null){const n=e.cameras[0].viewport,r=new Di({vertexShader:uE,fragmentShader:cE,uniforms:{depthColor:{value:this.texture},depthWidth:{value:n.z},depthHeight:{value:n.w}}});this.mesh=new ii(new zl(20,20),r)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}}class dE extends Ys{constructor(e,n){super();const r=this;let o=null,u=1,c=null,d="local-floor",p=1,m=null,x=null,S=null,g=null,y=null,M=null;const C=typeof XRWebGLBinding<"u",_=new fE,v={},R=n.getContextAttributes();let L=null,b=null;const F=[],U=[],z=new Lt;let A=null;const D=new ti;D.viewport=new qt;const fe=new ti;fe.viewport=new qt;const O=[D,fe],te=new Tv;let Q=null,oe=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(ie){let me=F[ie];return me===void 0&&(me=new Fc,F[ie]=me),me.getTargetRaySpace()},this.getControllerGrip=function(ie){let me=F[ie];return me===void 0&&(me=new Fc,F[ie]=me),me.getGripSpace()},this.getHand=function(ie){let me=F[ie];return me===void 0&&(me=new Fc,F[ie]=me),me.getHandSpace()};function K(ie){const me=U.indexOf(ie.inputSource);if(me===-1)return;const pe=F[me];pe!==void 0&&(pe.update(ie.inputSource,ie.frame,m||c),pe.dispatchEvent({type:ie.type,data:ie.inputSource}))}function ee(){o.removeEventListener("select",K),o.removeEventListener("selectstart",K),o.removeEventListener("selectend",K),o.removeEventListener("squeeze",K),o.removeEventListener("squeezestart",K),o.removeEventListener("squeezeend",K),o.removeEventListener("end",ee),o.removeEventListener("inputsourceschange",W);for(let ie=0;ie<F.length;ie++){const me=U[ie];me!==null&&(U[ie]=null,F[ie].disconnect(me))}Q=null,oe=null,_.reset();for(const ie in v)delete v[ie];e.setRenderTarget(L),y=null,g=null,S=null,o=null,b=null,Ze.stop(),r.isPresenting=!1,e.setPixelRatio(A),e.setSize(z.width,z.height,!1),r.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(ie){u=ie,r.isPresenting===!0&&ot("WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(ie){d=ie,r.isPresenting===!0&&ot("WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return m||c},this.setReferenceSpace=function(ie){m=ie},this.getBaseLayer=function(){return g!==null?g:y},this.getBinding=function(){return S===null&&C&&(S=new XRWebGLBinding(o,n)),S},this.getFrame=function(){return M},this.getSession=function(){return o},this.setSession=async function(ie){if(o=ie,o!==null){if(L=e.getRenderTarget(),o.addEventListener("select",K),o.addEventListener("selectstart",K),o.addEventListener("selectend",K),o.addEventListener("squeeze",K),o.addEventListener("squeezestart",K),o.addEventListener("squeezeend",K),o.addEventListener("end",ee),o.addEventListener("inputsourceschange",W),R.xrCompatible!==!0&&await n.makeXRCompatible(),A=e.getPixelRatio(),e.getSize(z),C&&"createProjectionLayer"in XRWebGLBinding.prototype){let pe=null,Fe=null,He=null;R.depth&&(He=R.stencil?n.DEPTH24_STENCIL8:n.DEPTH_COMPONENT24,pe=R.stencil?es:Zi,Fe=R.stencil?Va:Pi);const nt={colorFormat:n.RGBA8,depthFormat:He,scaleFactor:u};S=this.getBinding(),g=S.createProjectionLayer(nt),o.updateRenderState({layers:[g]}),e.setPixelRatio(1),e.setSize(g.textureWidth,g.textureHeight,!1),b=new bi(g.textureWidth,g.textureHeight,{format:mi,type:ni,depthTexture:new Ha(g.textureWidth,g.textureHeight,Fe,void 0,void 0,void 0,void 0,void 0,void 0,pe),stencilBuffer:R.stencil,colorSpace:e.outputColorSpace,samples:R.antialias?4:0,resolveDepthBuffer:g.ignoreDepthValues===!1,resolveStencilBuffer:g.ignoreDepthValues===!1})}else{const pe={antialias:R.antialias,alpha:!0,depth:R.depth,stencil:R.stencil,framebufferScaleFactor:u};y=new XRWebGLLayer(o,n,pe),o.updateRenderState({baseLayer:y}),e.setPixelRatio(1),e.setSize(y.framebufferWidth,y.framebufferHeight,!1),b=new bi(y.framebufferWidth,y.framebufferHeight,{format:mi,type:ni,colorSpace:e.outputColorSpace,stencilBuffer:R.stencil,resolveDepthBuffer:y.ignoreDepthValues===!1,resolveStencilBuffer:y.ignoreDepthValues===!1})}b.isXRRenderTarget=!0,this.setFoveation(p),m=null,c=await o.requestReferenceSpace(d),Ze.setContext(o),Ze.start(),r.isPresenting=!0,r.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(o!==null)return o.environmentBlendMode},this.getDepthTexture=function(){return _.getDepthTexture()};function W(ie){for(let me=0;me<ie.removed.length;me++){const pe=ie.removed[me],Fe=U.indexOf(pe);Fe>=0&&(U[Fe]=null,F[Fe].disconnect(pe))}for(let me=0;me<ie.added.length;me++){const pe=ie.added[me];let Fe=U.indexOf(pe);if(Fe===-1){for(let nt=0;nt<F.length;nt++)if(nt>=U.length){U.push(pe),Fe=nt;break}else if(U[nt]===null){U[nt]=pe,Fe=nt;break}if(Fe===-1)break}const He=F[Fe];He&&He.connect(pe)}}const q=new ne,ae=new ne;function le(ie,me,pe){q.setFromMatrixPosition(me.matrixWorld),ae.setFromMatrixPosition(pe.matrixWorld);const Fe=q.distanceTo(ae),He=me.projectionMatrix.elements,nt=pe.projectionMatrix.elements,Wt=He[14]/(He[10]-1),ht=He[14]/(He[10]+1),xt=(He[9]+1)/He[5],Ct=(He[9]-1)/He[5],ut=(He[8]-1)/He[0],Ft=(nt[8]+1)/nt[0],k=Wt*ut,kt=Wt*Ft,mt=Fe/(-ut+Ft),St=mt*-ut;if(me.matrixWorld.decompose(ie.position,ie.quaternion,ie.scale),ie.translateX(St),ie.translateZ(mt),ie.matrixWorld.compose(ie.position,ie.quaternion,ie.scale),ie.matrixWorldInverse.copy(ie.matrixWorld).invert(),He[10]===-1)ie.projectionMatrix.copy(me.projectionMatrix),ie.projectionMatrixInverse.copy(me.projectionMatrixInverse);else{const Ge=Wt+mt,P=ht+mt,E=k-St,G=kt+(Fe-St),de=xt*ht/P*Ge,ge=Ct*ht/P*Ge;ie.projectionMatrix.makePerspective(E,G,de,ge,Ge,P),ie.projectionMatrixInverse.copy(ie.projectionMatrix).invert()}}function I(ie,me){me===null?ie.matrixWorld.copy(ie.matrix):ie.matrixWorld.multiplyMatrices(me.matrixWorld,ie.matrix),ie.matrixWorldInverse.copy(ie.matrixWorld).invert()}this.updateCamera=function(ie){if(o===null)return;let me=ie.near,pe=ie.far;_.texture!==null&&(_.depthNear>0&&(me=_.depthNear),_.depthFar>0&&(pe=_.depthFar)),te.near=fe.near=D.near=me,te.far=fe.far=D.far=pe,(Q!==te.near||oe!==te.far)&&(o.updateRenderState({depthNear:te.near,depthFar:te.far}),Q=te.near,oe=te.far),te.layers.mask=ie.layers.mask|6,D.layers.mask=te.layers.mask&-5,fe.layers.mask=te.layers.mask&-3;const Fe=ie.parent,He=te.cameras;I(te,Fe);for(let nt=0;nt<He.length;nt++)I(He[nt],Fe);He.length===2?le(te,D,fe):te.projectionMatrix.copy(D.projectionMatrix),j(ie,te,Fe)};function j(ie,me,pe){pe===null?ie.matrix.copy(me.matrixWorld):(ie.matrix.copy(pe.matrixWorld),ie.matrix.invert(),ie.matrix.multiply(me.matrixWorld)),ie.matrix.decompose(ie.position,ie.quaternion,ie.scale),ie.updateMatrixWorld(!0),ie.projectionMatrix.copy(me.projectionMatrix),ie.projectionMatrixInverse.copy(me.projectionMatrixInverse),ie.isPerspectiveCamera&&(ie.fov=$f*2*Math.atan(1/ie.projectionMatrix.elements[5]),ie.zoom=1)}this.getCamera=function(){return te},this.getFoveation=function(){if(!(g===null&&y===null))return p},this.setFoveation=function(ie){p=ie,g!==null&&(g.fixedFoveation=ie),y!==null&&y.fixedFoveation!==void 0&&(y.fixedFoveation=ie)},this.hasDepthSensing=function(){return _.texture!==null},this.getDepthSensingMesh=function(){return _.getMesh(te)},this.getCameraTexture=function(ie){return v[ie]};let Ce=null;function Xe(ie,me){if(x=me.getViewerPose(m||c),M=me,x!==null){const pe=x.views;y!==null&&(e.setRenderTargetFramebuffer(b,y.framebuffer),e.setRenderTarget(b));let Fe=!1;pe.length!==te.cameras.length&&(te.cameras.length=0,Fe=!0);for(let ht=0;ht<pe.length;ht++){const xt=pe[ht];let Ct=null;if(y!==null)Ct=y.getViewport(xt);else{const Ft=S.getViewSubImage(g,xt);Ct=Ft.viewport,ht===0&&(e.setRenderTargetTextures(b,Ft.colorTexture,Ft.depthStencilTexture),e.setRenderTarget(b))}let ut=O[ht];ut===void 0&&(ut=new ti,ut.layers.enable(ht),ut.viewport=new qt,O[ht]=ut),ut.matrix.fromArray(xt.transform.matrix),ut.matrix.decompose(ut.position,ut.quaternion,ut.scale),ut.projectionMatrix.fromArray(xt.projectionMatrix),ut.projectionMatrixInverse.copy(ut.projectionMatrix).invert(),ut.viewport.set(Ct.x,Ct.y,Ct.width,Ct.height),ht===0&&(te.matrix.copy(ut.matrix),te.matrix.decompose(te.position,te.quaternion,te.scale)),Fe===!0&&te.cameras.push(ut)}const He=o.enabledFeatures;if(He&&He.includes("depth-sensing")&&o.depthUsage=="gpu-optimized"&&C){S=r.getBinding();const ht=S.getDepthInformation(pe[0]);ht&&ht.isValid&&ht.texture&&_.init(ht,o.renderState)}if(He&&He.includes("camera-access")&&C){e.state.unbindTexture(),S=r.getBinding();for(let ht=0;ht<pe.length;ht++){const xt=pe[ht].camera;if(xt){let Ct=v[xt];Ct||(Ct=new lg,v[xt]=Ct);const ut=S.getCameraImage(xt);Ct.sourceTexture=ut}}}}for(let pe=0;pe<F.length;pe++){const Fe=U[pe],He=F[pe];Fe!==null&&He!==void 0&&He.update(Fe,me,m||c)}Ce&&Ce(ie,me),me.detectedPlanes&&r.dispatchEvent({type:"planesdetected",data:me}),M=null}const Ze=new dg;Ze.setAnimationLoop(Xe),this.setAnimationLoop=function(ie){Ce=ie},this.dispose=function(){}}}const $r=new Qi,hE=new $t;function pE(s,e){function n(_,v){_.matrixAutoUpdate===!0&&_.updateMatrix(),v.value.copy(_.matrix)}function r(_,v){v.color.getRGB(_.fogColor.value,ug(s)),v.isFog?(_.fogNear.value=v.near,_.fogFar.value=v.far):v.isFogExp2&&(_.fogDensity.value=v.density)}function o(_,v,R,L,b){v.isMeshBasicMaterial?u(_,v):v.isMeshLambertMaterial?(u(_,v),v.envMap&&(_.envMapIntensity.value=v.envMapIntensity)):v.isMeshToonMaterial?(u(_,v),S(_,v)):v.isMeshPhongMaterial?(u(_,v),x(_,v),v.envMap&&(_.envMapIntensity.value=v.envMapIntensity)):v.isMeshStandardMaterial?(u(_,v),g(_,v),v.isMeshPhysicalMaterial&&y(_,v,b)):v.isMeshMatcapMaterial?(u(_,v),M(_,v)):v.isMeshDepthMaterial?u(_,v):v.isMeshDistanceMaterial?(u(_,v),C(_,v)):v.isMeshNormalMaterial?u(_,v):v.isLineBasicMaterial?(c(_,v),v.isLineDashedMaterial&&d(_,v)):v.isPointsMaterial?p(_,v,R,L):v.isSpriteMaterial?m(_,v):v.isShadowMaterial?(_.color.value.copy(v.color),_.opacity.value=v.opacity):v.isShaderMaterial&&(v.uniformsNeedUpdate=!1)}function u(_,v){_.opacity.value=v.opacity,v.color&&_.diffuse.value.copy(v.color),v.emissive&&_.emissive.value.copy(v.emissive).multiplyScalar(v.emissiveIntensity),v.map&&(_.map.value=v.map,n(v.map,_.mapTransform)),v.alphaMap&&(_.alphaMap.value=v.alphaMap,n(v.alphaMap,_.alphaMapTransform)),v.bumpMap&&(_.bumpMap.value=v.bumpMap,n(v.bumpMap,_.bumpMapTransform),_.bumpScale.value=v.bumpScale,v.side===In&&(_.bumpScale.value*=-1)),v.normalMap&&(_.normalMap.value=v.normalMap,n(v.normalMap,_.normalMapTransform),_.normalScale.value.copy(v.normalScale),v.side===In&&_.normalScale.value.negate()),v.displacementMap&&(_.displacementMap.value=v.displacementMap,n(v.displacementMap,_.displacementMapTransform),_.displacementScale.value=v.displacementScale,_.displacementBias.value=v.displacementBias),v.emissiveMap&&(_.emissiveMap.value=v.emissiveMap,n(v.emissiveMap,_.emissiveMapTransform)),v.specularMap&&(_.specularMap.value=v.specularMap,n(v.specularMap,_.specularMapTransform)),v.alphaTest>0&&(_.alphaTest.value=v.alphaTest);const R=e.get(v),L=R.envMap,b=R.envMapRotation;L&&(_.envMap.value=L,$r.copy(b),$r.x*=-1,$r.y*=-1,$r.z*=-1,L.isCubeTexture&&L.isRenderTargetTexture===!1&&($r.y*=-1,$r.z*=-1),_.envMapRotation.value.setFromMatrix4(hE.makeRotationFromEuler($r)),_.flipEnvMap.value=L.isCubeTexture&&L.isRenderTargetTexture===!1?-1:1,_.reflectivity.value=v.reflectivity,_.ior.value=v.ior,_.refractionRatio.value=v.refractionRatio),v.lightMap&&(_.lightMap.value=v.lightMap,_.lightMapIntensity.value=v.lightMapIntensity,n(v.lightMap,_.lightMapTransform)),v.aoMap&&(_.aoMap.value=v.aoMap,_.aoMapIntensity.value=v.aoMapIntensity,n(v.aoMap,_.aoMapTransform))}function c(_,v){_.diffuse.value.copy(v.color),_.opacity.value=v.opacity,v.map&&(_.map.value=v.map,n(v.map,_.mapTransform))}function d(_,v){_.dashSize.value=v.dashSize,_.totalSize.value=v.dashSize+v.gapSize,_.scale.value=v.scale}function p(_,v,R,L){_.diffuse.value.copy(v.color),_.opacity.value=v.opacity,_.size.value=v.size*R,_.scale.value=L*.5,v.map&&(_.map.value=v.map,n(v.map,_.uvTransform)),v.alphaMap&&(_.alphaMap.value=v.alphaMap,n(v.alphaMap,_.alphaMapTransform)),v.alphaTest>0&&(_.alphaTest.value=v.alphaTest)}function m(_,v){_.diffuse.value.copy(v.color),_.opacity.value=v.opacity,_.rotation.value=v.rotation,v.map&&(_.map.value=v.map,n(v.map,_.mapTransform)),v.alphaMap&&(_.alphaMap.value=v.alphaMap,n(v.alphaMap,_.alphaMapTransform)),v.alphaTest>0&&(_.alphaTest.value=v.alphaTest)}function x(_,v){_.specular.value.copy(v.specular),_.shininess.value=Math.max(v.shininess,1e-4)}function S(_,v){v.gradientMap&&(_.gradientMap.value=v.gradientMap)}function g(_,v){_.metalness.value=v.metalness,v.metalnessMap&&(_.metalnessMap.value=v.metalnessMap,n(v.metalnessMap,_.metalnessMapTransform)),_.roughness.value=v.roughness,v.roughnessMap&&(_.roughnessMap.value=v.roughnessMap,n(v.roughnessMap,_.roughnessMapTransform)),v.envMap&&(_.envMapIntensity.value=v.envMapIntensity)}function y(_,v,R){_.ior.value=v.ior,v.sheen>0&&(_.sheenColor.value.copy(v.sheenColor).multiplyScalar(v.sheen),_.sheenRoughness.value=v.sheenRoughness,v.sheenColorMap&&(_.sheenColorMap.value=v.sheenColorMap,n(v.sheenColorMap,_.sheenColorMapTransform)),v.sheenRoughnessMap&&(_.sheenRoughnessMap.value=v.sheenRoughnessMap,n(v.sheenRoughnessMap,_.sheenRoughnessMapTransform))),v.clearcoat>0&&(_.clearcoat.value=v.clearcoat,_.clearcoatRoughness.value=v.clearcoatRoughness,v.clearcoatMap&&(_.clearcoatMap.value=v.clearcoatMap,n(v.clearcoatMap,_.clearcoatMapTransform)),v.clearcoatRoughnessMap&&(_.clearcoatRoughnessMap.value=v.clearcoatRoughnessMap,n(v.clearcoatRoughnessMap,_.clearcoatRoughnessMapTransform)),v.clearcoatNormalMap&&(_.clearcoatNormalMap.value=v.clearcoatNormalMap,n(v.clearcoatNormalMap,_.clearcoatNormalMapTransform),_.clearcoatNormalScale.value.copy(v.clearcoatNormalScale),v.side===In&&_.clearcoatNormalScale.value.negate())),v.dispersion>0&&(_.dispersion.value=v.dispersion),v.iridescence>0&&(_.iridescence.value=v.iridescence,_.iridescenceIOR.value=v.iridescenceIOR,_.iridescenceThicknessMinimum.value=v.iridescenceThicknessRange[0],_.iridescenceThicknessMaximum.value=v.iridescenceThicknessRange[1],v.iridescenceMap&&(_.iridescenceMap.value=v.iridescenceMap,n(v.iridescenceMap,_.iridescenceMapTransform)),v.iridescenceThicknessMap&&(_.iridescenceThicknessMap.value=v.iridescenceThicknessMap,n(v.iridescenceThicknessMap,_.iridescenceThicknessMapTransform))),v.transmission>0&&(_.transmission.value=v.transmission,_.transmissionSamplerMap.value=R.texture,_.transmissionSamplerSize.value.set(R.width,R.height),v.transmissionMap&&(_.transmissionMap.value=v.transmissionMap,n(v.transmissionMap,_.transmissionMapTransform)),_.thickness.value=v.thickness,v.thicknessMap&&(_.thicknessMap.value=v.thicknessMap,n(v.thicknessMap,_.thicknessMapTransform)),_.attenuationDistance.value=v.attenuationDistance,_.attenuationColor.value.copy(v.attenuationColor)),v.anisotropy>0&&(_.anisotropyVector.value.set(v.anisotropy*Math.cos(v.anisotropyRotation),v.anisotropy*Math.sin(v.anisotropyRotation)),v.anisotropyMap&&(_.anisotropyMap.value=v.anisotropyMap,n(v.anisotropyMap,_.anisotropyMapTransform))),_.specularIntensity.value=v.specularIntensity,_.specularColor.value.copy(v.specularColor),v.specularColorMap&&(_.specularColorMap.value=v.specularColorMap,n(v.specularColorMap,_.specularColorMapTransform)),v.specularIntensityMap&&(_.specularIntensityMap.value=v.specularIntensityMap,n(v.specularIntensityMap,_.specularIntensityMapTransform))}function M(_,v){v.matcap&&(_.matcap.value=v.matcap)}function C(_,v){const R=e.get(v).light;_.referencePosition.value.setFromMatrixPosition(R.matrixWorld),_.nearDistance.value=R.shadow.camera.near,_.farDistance.value=R.shadow.camera.far}return{refreshFogUniforms:r,refreshMaterialUniforms:o}}function mE(s,e,n,r){let o={},u={},c=[];const d=s.getParameter(s.MAX_UNIFORM_BUFFER_BINDINGS);function p(R,L){const b=L.program;r.uniformBlockBinding(R,b)}function m(R,L){let b=o[R.id];b===void 0&&(M(R),b=x(R),o[R.id]=b,R.addEventListener("dispose",_));const F=L.program;r.updateUBOMapping(R,F);const U=e.render.frame;u[R.id]!==U&&(g(R),u[R.id]=U)}function x(R){const L=S();R.__bindingPointIndex=L;const b=s.createBuffer(),F=R.__size,U=R.usage;return s.bindBuffer(s.UNIFORM_BUFFER,b),s.bufferData(s.UNIFORM_BUFFER,F,U),s.bindBuffer(s.UNIFORM_BUFFER,null),s.bindBufferBase(s.UNIFORM_BUFFER,L,b),b}function S(){for(let R=0;R<d;R++)if(c.indexOf(R)===-1)return c.push(R),R;return wt("WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function g(R){const L=o[R.id],b=R.uniforms,F=R.__cache;s.bindBuffer(s.UNIFORM_BUFFER,L);for(let U=0,z=b.length;U<z;U++){const A=Array.isArray(b[U])?b[U]:[b[U]];for(let D=0,fe=A.length;D<fe;D++){const O=A[D];if(y(O,U,D,F)===!0){const te=O.__offset,Q=Array.isArray(O.value)?O.value:[O.value];let oe=0;for(let K=0;K<Q.length;K++){const ee=Q[K],W=C(ee);typeof ee=="number"||typeof ee=="boolean"?(O.__data[0]=ee,s.bufferSubData(s.UNIFORM_BUFFER,te+oe,O.__data)):ee.isMatrix3?(O.__data[0]=ee.elements[0],O.__data[1]=ee.elements[1],O.__data[2]=ee.elements[2],O.__data[3]=0,O.__data[4]=ee.elements[3],O.__data[5]=ee.elements[4],O.__data[6]=ee.elements[5],O.__data[7]=0,O.__data[8]=ee.elements[6],O.__data[9]=ee.elements[7],O.__data[10]=ee.elements[8],O.__data[11]=0):(ee.toArray(O.__data,oe),oe+=W.storage/Float32Array.BYTES_PER_ELEMENT)}s.bufferSubData(s.UNIFORM_BUFFER,te,O.__data)}}}s.bindBuffer(s.UNIFORM_BUFFER,null)}function y(R,L,b,F){const U=R.value,z=L+"_"+b;if(F[z]===void 0)return typeof U=="number"||typeof U=="boolean"?F[z]=U:F[z]=U.clone(),!0;{const A=F[z];if(typeof U=="number"||typeof U=="boolean"){if(A!==U)return F[z]=U,!0}else if(A.equals(U)===!1)return A.copy(U),!0}return!1}function M(R){const L=R.uniforms;let b=0;const F=16;for(let z=0,A=L.length;z<A;z++){const D=Array.isArray(L[z])?L[z]:[L[z]];for(let fe=0,O=D.length;fe<O;fe++){const te=D[fe],Q=Array.isArray(te.value)?te.value:[te.value];for(let oe=0,K=Q.length;oe<K;oe++){const ee=Q[oe],W=C(ee),q=b%F,ae=q%W.boundary,le=q+ae;b+=ae,le!==0&&F-le<W.storage&&(b+=F-le),te.__data=new Float32Array(W.storage/Float32Array.BYTES_PER_ELEMENT),te.__offset=b,b+=W.storage}}}const U=b%F;return U>0&&(b+=F-U),R.__size=b,R.__cache={},this}function C(R){const L={boundary:0,storage:0};return typeof R=="number"||typeof R=="boolean"?(L.boundary=4,L.storage=4):R.isVector2?(L.boundary=8,L.storage=8):R.isVector3||R.isColor?(L.boundary=16,L.storage=12):R.isVector4?(L.boundary=16,L.storage=16):R.isMatrix3?(L.boundary=48,L.storage=48):R.isMatrix4?(L.boundary=64,L.storage=64):R.isTexture?ot("WebGLRenderer: Texture samplers can not be part of an uniforms group."):ot("WebGLRenderer: Unsupported uniform value type.",R),L}function _(R){const L=R.target;L.removeEventListener("dispose",_);const b=c.indexOf(L.__bindingPointIndex);c.splice(b,1),s.deleteBuffer(o[L.id]),delete o[L.id],delete u[L.id]}function v(){for(const R in o)s.deleteBuffer(o[R]);c=[],o={},u={}}return{bind:p,update:m,dispose:v}}const gE=new Uint16Array([12469,15057,12620,14925,13266,14620,13807,14376,14323,13990,14545,13625,14713,13328,14840,12882,14931,12528,14996,12233,15039,11829,15066,11525,15080,11295,15085,10976,15082,10705,15073,10495,13880,14564,13898,14542,13977,14430,14158,14124,14393,13732,14556,13410,14702,12996,14814,12596,14891,12291,14937,11834,14957,11489,14958,11194,14943,10803,14921,10506,14893,10278,14858,9960,14484,14039,14487,14025,14499,13941,14524,13740,14574,13468,14654,13106,14743,12678,14818,12344,14867,11893,14889,11509,14893,11180,14881,10751,14852,10428,14812,10128,14765,9754,14712,9466,14764,13480,14764,13475,14766,13440,14766,13347,14769,13070,14786,12713,14816,12387,14844,11957,14860,11549,14868,11215,14855,10751,14825,10403,14782,10044,14729,9651,14666,9352,14599,9029,14967,12835,14966,12831,14963,12804,14954,12723,14936,12564,14917,12347,14900,11958,14886,11569,14878,11247,14859,10765,14828,10401,14784,10011,14727,9600,14660,9289,14586,8893,14508,8533,15111,12234,15110,12234,15104,12216,15092,12156,15067,12010,15028,11776,14981,11500,14942,11205,14902,10752,14861,10393,14812,9991,14752,9570,14682,9252,14603,8808,14519,8445,14431,8145,15209,11449,15208,11451,15202,11451,15190,11438,15163,11384,15117,11274,15055,10979,14994,10648,14932,10343,14871,9936,14803,9532,14729,9218,14645,8742,14556,8381,14461,8020,14365,7603,15273,10603,15272,10607,15267,10619,15256,10631,15231,10614,15182,10535,15118,10389,15042,10167,14963,9787,14883,9447,14800,9115,14710,8665,14615,8318,14514,7911,14411,7507,14279,7198,15314,9675,15313,9683,15309,9712,15298,9759,15277,9797,15229,9773,15166,9668,15084,9487,14995,9274,14898,8910,14800,8539,14697,8234,14590,7790,14479,7409,14367,7067,14178,6621,15337,8619,15337,8631,15333,8677,15325,8769,15305,8871,15264,8940,15202,8909,15119,8775,15022,8565,14916,8328,14804,8009,14688,7614,14569,7287,14448,6888,14321,6483,14088,6171,15350,7402,15350,7419,15347,7480,15340,7613,15322,7804,15287,7973,15229,8057,15148,8012,15046,7846,14933,7611,14810,7357,14682,7069,14552,6656,14421,6316,14251,5948,14007,5528,15356,5942,15356,5977,15353,6119,15348,6294,15332,6551,15302,6824,15249,7044,15171,7122,15070,7050,14949,6861,14818,6611,14679,6349,14538,6067,14398,5651,14189,5311,13935,4958,15359,4123,15359,4153,15356,4296,15353,4646,15338,5160,15311,5508,15263,5829,15188,6042,15088,6094,14966,6001,14826,5796,14678,5543,14527,5287,14377,4985,14133,4586,13869,4257,15360,1563,15360,1642,15358,2076,15354,2636,15341,3350,15317,4019,15273,4429,15203,4732,15105,4911,14981,4932,14836,4818,14679,4621,14517,4386,14359,4156,14083,3795,13808,3437,15360,122,15360,137,15358,285,15355,636,15344,1274,15322,2177,15281,2765,15215,3223,15120,3451,14995,3569,14846,3567,14681,3466,14511,3305,14344,3121,14037,2800,13753,2467,15360,0,15360,1,15359,21,15355,89,15346,253,15325,479,15287,796,15225,1148,15133,1492,15008,1749,14856,1882,14685,1886,14506,1783,14324,1608,13996,1398,13702,1183]);let Ei=null;function _E(){return Ei===null&&(Ei=new cv(gE,16,16,Ws,Ki),Ei.name="DFG_LUT",Ei.minFilter=_n,Ei.magFilter=_n,Ei.wrapS=Yi,Ei.wrapT=Yi,Ei.generateMipmaps=!1,Ei.needsUpdate=!0),Ei}class vE{constructor(e={}){const{canvas:n=V0(),context:r=null,depth:o=!0,stencil:u=!1,alpha:c=!1,antialias:d=!1,premultipliedAlpha:p=!0,preserveDrawingBuffer:m=!1,powerPreference:x="default",failIfMajorPerformanceCaveat:S=!1,reversedDepthBuffer:g=!1,outputBufferType:y=ni}=e;this.isWebGLRenderer=!0;let M;if(r!==null){if(typeof WebGLRenderingContext<"u"&&r instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");M=r.getContextAttributes().alpha}else M=c;const C=y,_=new Set([ad,sd,rd]),v=new Set([ni,Pi,za,Va,nd,id]),R=new Uint32Array(4),L=new Int32Array(4);let b=null,F=null;const U=[],z=[];let A=null;this.domElement=n,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=Ri,this.toneMappingExposure=1,this.transmissionResolutionScale=1;const D=this;let fe=!1;this._outputColorSpace=ei;let O=0,te=0,Q=null,oe=-1,K=null;const ee=new qt,W=new qt;let q=null;const ae=new bt(0);let le=0,I=n.width,j=n.height,Ce=1,Xe=null,Ze=null;const ie=new qt(0,0,I,j),me=new qt(0,0,I,j);let pe=!1;const Fe=new sg;let He=!1,nt=!1;const Wt=new $t,ht=new ne,xt=new qt,Ct={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};let ut=!1;function Ft(){return Q===null?Ce:1}let k=r;function kt(w,X){return n.getContext(w,X)}try{const w={alpha:!0,depth:o,stencil:u,antialias:d,premultipliedAlpha:p,preserveDrawingBuffer:m,powerPreference:x,failIfMajorPerformanceCaveat:S};if("setAttribute"in n&&n.setAttribute("data-engine",`three.js r${ed}`),n.addEventListener("webglcontextlost",ze,!1),n.addEventListener("webglcontextrestored",rt,!1),n.addEventListener("webglcontextcreationerror",Pt,!1),k===null){const X="webgl2";if(k=kt(X,w),k===null)throw kt(X)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(w){throw wt("WebGLRenderer: "+w.message),w}let mt,St,Ge,P,E,G,de,ge,ue,Be,we,qe,it,Se,Te,We,ke,De,lt,V,Ae,Me,Le;function ye(){mt=new vy(k),mt.init(),Ae=new lE(k,mt),St=new cy(k,mt,e,Ae),Ge=new aE(k,mt),St.reversedDepthBuffer&&g&&Ge.buffers.depth.setReversed(!0),P=new yy(k),E=new jM,G=new oE(k,mt,Ge,E,St,Ae,P),de=new _y(D),ge=new Av(k),Me=new ly(k,ge),ue=new xy(k,ge,P,Me),Be=new Ey(k,ue,ge,Me,P),De=new My(k,St,G),Te=new fy(E),we=new XM(D,de,mt,St,Me,Te),qe=new pE(D,E),it=new qM,Se=new eE(mt),ke=new oy(D,de,Ge,Be,M,p),We=new sE(D,Be,St),Le=new mE(k,P,St,Ge),lt=new uy(k,mt,P),V=new Sy(k,mt,P),P.programs=we.programs,D.capabilities=St,D.extensions=mt,D.properties=E,D.renderLists=it,D.shadowMap=We,D.state=Ge,D.info=P}ye(),C!==ni&&(A=new wy(C,n.width,n.height,o,u));const ce=new dE(D,k);this.xr=ce,this.getContext=function(){return k},this.getContextAttributes=function(){return k.getContextAttributes()},this.forceContextLoss=function(){const w=mt.get("WEBGL_lose_context");w&&w.loseContext()},this.forceContextRestore=function(){const w=mt.get("WEBGL_lose_context");w&&w.restoreContext()},this.getPixelRatio=function(){return Ce},this.setPixelRatio=function(w){w!==void 0&&(Ce=w,this.setSize(I,j,!1))},this.getSize=function(w){return w.set(I,j)},this.setSize=function(w,X,se=!0){if(ce.isPresenting){ot("WebGLRenderer: Can't change size while VR device is presenting.");return}I=w,j=X,n.width=Math.floor(w*Ce),n.height=Math.floor(X*Ce),se===!0&&(n.style.width=w+"px",n.style.height=X+"px"),A!==null&&A.setSize(n.width,n.height),this.setViewport(0,0,w,X)},this.getDrawingBufferSize=function(w){return w.set(I*Ce,j*Ce).floor()},this.setDrawingBufferSize=function(w,X,se){I=w,j=X,Ce=se,n.width=Math.floor(w*se),n.height=Math.floor(X*se),this.setViewport(0,0,w,X)},this.setEffects=function(w){if(C===ni){console.error("THREE.WebGLRenderer: setEffects() requires outputBufferType set to HalfFloatType or FloatType.");return}if(w){for(let X=0;X<w.length;X++)if(w[X].isOutputPass===!0){console.warn("THREE.WebGLRenderer: OutputPass is not needed in setEffects(). Tone mapping and color space conversion are applied automatically.");break}}A.setEffects(w||[])},this.getCurrentViewport=function(w){return w.copy(ee)},this.getViewport=function(w){return w.copy(ie)},this.setViewport=function(w,X,se,J){w.isVector4?ie.set(w.x,w.y,w.z,w.w):ie.set(w,X,se,J),Ge.viewport(ee.copy(ie).multiplyScalar(Ce).round())},this.getScissor=function(w){return w.copy(me)},this.setScissor=function(w,X,se,J){w.isVector4?me.set(w.x,w.y,w.z,w.w):me.set(w,X,se,J),Ge.scissor(W.copy(me).multiplyScalar(Ce).round())},this.getScissorTest=function(){return pe},this.setScissorTest=function(w){Ge.setScissorTest(pe=w)},this.setOpaqueSort=function(w){Xe=w},this.setTransparentSort=function(w){Ze=w},this.getClearColor=function(w){return w.copy(ke.getClearColor())},this.setClearColor=function(){ke.setClearColor(...arguments)},this.getClearAlpha=function(){return ke.getClearAlpha()},this.setClearAlpha=function(){ke.setClearAlpha(...arguments)},this.clear=function(w=!0,X=!0,se=!0){let J=0;if(w){let $=!1;if(Q!==null){const be=Q.texture.format;$=_.has(be)}if($){const be=Q.texture.type,Ue=v.has(be),Re=ke.getClearColor(),Ne=ke.getClearAlpha(),Ke=Re.r,Je=Re.g,ct=Re.b;Ue?(R[0]=Ke,R[1]=Je,R[2]=ct,R[3]=Ne,k.clearBufferuiv(k.COLOR,0,R)):(L[0]=Ke,L[1]=Je,L[2]=ct,L[3]=Ne,k.clearBufferiv(k.COLOR,0,L))}else J|=k.COLOR_BUFFER_BIT}X&&(J|=k.DEPTH_BUFFER_BIT),se&&(J|=k.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),J!==0&&k.clear(J)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){n.removeEventListener("webglcontextlost",ze,!1),n.removeEventListener("webglcontextrestored",rt,!1),n.removeEventListener("webglcontextcreationerror",Pt,!1),ke.dispose(),it.dispose(),Se.dispose(),E.dispose(),de.dispose(),Be.dispose(),Me.dispose(),Le.dispose(),we.dispose(),ce.dispose(),ce.removeEventListener("sessionstart",Ji),ce.removeEventListener("sessionend",br),Xn.stop()};function ze(w){w.preventDefault(),jp("WebGLRenderer: Context Lost."),fe=!0}function rt(){jp("WebGLRenderer: Context Restored."),fe=!1;const w=P.autoReset,X=We.enabled,se=We.autoUpdate,J=We.needsUpdate,$=We.type;ye(),P.autoReset=w,We.enabled=X,We.autoUpdate=se,We.needsUpdate=J,We.type=$}function Pt(w){wt("WebGLRenderer: A WebGL context could not be created. Reason: ",w.statusMessage)}function yt(w){const X=w.target;X.removeEventListener("dispose",yt),Wn(X)}function Wn(w){vn(w),E.remove(w)}function vn(w){const X=E.get(w).programs;X!==void 0&&(X.forEach(function(se){we.releaseProgram(se)}),w.isShaderMaterial&&we.releaseShaderCache(w))}this.renderBufferDirect=function(w,X,se,J,$,be){X===null&&(X=Ct);const Ue=$.isMesh&&$.matrixWorld.determinant()<0,Re=Ka(w,X,se,J,$);Ge.setMaterial(J,Ue);let Ne=se.index,Ke=1;if(J.wireframe===!0){if(Ne=ue.getWireframeAttribute(se),Ne===void 0)return;Ke=2}const Je=se.drawRange,ct=se.attributes.position;let Qe=Je.start*Ke,Rt=(Je.start+Je.count)*Ke;be!==null&&(Qe=Math.max(Qe,be.start*Ke),Rt=Math.min(Rt,(be.start+be.count)*Ke)),Ne!==null?(Qe=Math.max(Qe,0),Rt=Math.min(Rt,Ne.count)):ct!=null&&(Qe=Math.max(Qe,0),Rt=Math.min(Rt,ct.count));const It=Rt-Qe;if(It<0||It===1/0)return;Me.setup($,J,Re,se,Ne);let Nt,vt=lt;if(Ne!==null&&(Nt=ge.get(Ne),vt=V,vt.setIndex(Nt)),$.isMesh)J.wireframe===!0?(Ge.setLineWidth(J.wireframeLinewidth*Ft()),vt.setMode(k.LINES)):vt.setMode(k.TRIANGLES);else if($.isLine){let Xt=J.linewidth;Xt===void 0&&(Xt=1),Ge.setLineWidth(Xt*Ft()),$.isLineSegments?vt.setMode(k.LINES):$.isLineLoop?vt.setMode(k.LINE_LOOP):vt.setMode(k.LINE_STRIP)}else $.isPoints?vt.setMode(k.POINTS):$.isSprite&&vt.setMode(k.TRIANGLES);if($.isBatchedMesh)if($._multiDrawInstances!==null)Fl("WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."),vt.renderMultiDrawInstances($._multiDrawStarts,$._multiDrawCounts,$._multiDrawCount,$._multiDrawInstances);else if(mt.get("WEBGL_multi_draw"))vt.renderMultiDraw($._multiDrawStarts,$._multiDrawCounts,$._multiDrawCount);else{const Xt=$._multiDrawStarts,Ye=$._multiDrawCounts,xn=$._multiDrawCount,gt=Ne?ge.get(Ne).bytesPerElement:1,wn=E.get(J).currentProgram.getUniforms();for(let An=0;An<xn;An++)wn.setValue(k,"_gl_DrawID",An),vt.render(Xt[An]/gt,Ye[An])}else if($.isInstancedMesh)vt.renderInstances(Qe,It,$.count);else if(se.isInstancedBufferGeometry){const Xt=se._maxInstanceCount!==void 0?se._maxInstanceCount:1/0,Ye=Math.min(se.instanceCount,Xt);vt.renderInstances(Qe,It,Ye)}else vt.render(Qe,It)};function ns(w,X,se){w.transparent===!0&&w.side===wi&&w.forceSinglePass===!1?(w.side=In,w.needsUpdate=!0,Dr(w,X,se),w.side=Rr,w.needsUpdate=!0,Dr(w,X,se),w.side=wi):Dr(w,X,se)}this.compile=function(w,X,se=null){se===null&&(se=w),F=Se.get(se),F.init(X),z.push(F),se.traverseVisible(function($){$.isLight&&$.layers.test(X.layers)&&(F.pushLight($),$.castShadow&&F.pushShadow($))}),w!==se&&w.traverseVisible(function($){$.isLight&&$.layers.test(X.layers)&&(F.pushLight($),$.castShadow&&F.pushShadow($))}),F.setupLights();const J=new Set;return w.traverse(function($){if(!($.isMesh||$.isPoints||$.isLine||$.isSprite))return;const be=$.material;if(be)if(Array.isArray(be))for(let Ue=0;Ue<be.length;Ue++){const Re=be[Ue];ns(Re,se,$),J.add(Re)}else ns(be,se,$),J.add(be)}),F=z.pop(),J},this.compileAsync=function(w,X,se=null){const J=this.compile(w,X,se);return new Promise($=>{function be(){if(J.forEach(function(Ue){E.get(Ue).currentProgram.isReady()&&J.delete(Ue)}),J.size===0){$(w);return}setTimeout(be,10)}mt.get("KHR_parallel_shader_compile")!==null?be():setTimeout(be,10)})};let Li=null;function Gl(w){Li&&Li(w)}function Ji(){Xn.stop()}function br(){Xn.start()}const Xn=new dg;Xn.setAnimationLoop(Gl),typeof self<"u"&&Xn.setContext(self),this.setAnimationLoop=function(w){Li=w,ce.setAnimationLoop(w),w===null?Xn.stop():Xn.start()},ce.addEventListener("sessionstart",Ji),ce.addEventListener("sessionend",br),this.render=function(w,X){if(X!==void 0&&X.isCamera!==!0){wt("WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(fe===!0)return;const se=ce.enabled===!0&&ce.isPresenting===!0,J=A!==null&&(Q===null||se)&&A.begin(D,Q);if(w.matrixWorldAutoUpdate===!0&&w.updateMatrixWorld(),X.parent===null&&X.matrixWorldAutoUpdate===!0&&X.updateMatrixWorld(),ce.enabled===!0&&ce.isPresenting===!0&&(A===null||A.isCompositing()===!1)&&(ce.cameraAutoUpdate===!0&&ce.updateCamera(X),X=ce.getCamera()),w.isScene===!0&&w.onBeforeRender(D,w,X,Q),F=Se.get(w,z.length),F.init(X),z.push(F),Wt.multiplyMatrices(X.projectionMatrix,X.matrixWorldInverse),Fe.setFromProjectionMatrix(Wt,Ci,X.reversedDepth),nt=this.localClippingEnabled,He=Te.init(this.clippingPlanes,nt),b=it.get(w,U.length),b.init(),U.push(b),ce.enabled===!0&&ce.isPresenting===!0){const Ue=D.xr.getDepthSensingMesh();Ue!==null&&Pr(Ue,X,-1/0,D.sortObjects)}Pr(w,X,0,D.sortObjects),b.finish(),D.sortObjects===!0&&b.sort(Xe,Ze),ut=ce.enabled===!1||ce.isPresenting===!1||ce.hasDepthSensing()===!1,ut&&ke.addToRenderList(b,w),this.info.render.frame++,He===!0&&Te.beginShadows();const $=F.state.shadowsArray;if(We.render($,w,X),He===!0&&Te.endShadows(),this.info.autoReset===!0&&this.info.reset(),(J&&A.hasRenderPass())===!1){const Ue=b.opaque,Re=b.transmissive;if(F.setupLights(),X.isArrayCamera){const Ne=X.cameras;if(Re.length>0)for(let Ke=0,Je=Ne.length;Ke<Je;Ke++){const ct=Ne[Ke];qa(Ue,Re,w,ct)}ut&&ke.render(w);for(let Ke=0,Je=Ne.length;Ke<Je;Ke++){const ct=Ne[Ke];Ya(b,w,ct,ct.viewport)}}else Re.length>0&&qa(Ue,Re,w,X),ut&&ke.render(w),Ya(b,w,X)}Q!==null&&te===0&&(G.updateMultisampleRenderTarget(Q),G.updateRenderTargetMipmap(Q)),J&&A.end(D),w.isScene===!0&&w.onAfterRender(D,w,X),Me.resetDefaultState(),oe=-1,K=null,z.pop(),z.length>0?(F=z[z.length-1],He===!0&&Te.setGlobalState(D.clippingPlanes,F.state.camera)):F=null,U.pop(),U.length>0?b=U[U.length-1]:b=null};function Pr(w,X,se,J){if(w.visible===!1)return;if(w.layers.test(X.layers)){if(w.isGroup)se=w.renderOrder;else if(w.isLOD)w.autoUpdate===!0&&w.update(X);else if(w.isLight)F.pushLight(w),w.castShadow&&F.pushShadow(w);else if(w.isSprite){if(!w.frustumCulled||Fe.intersectsSprite(w)){J&&xt.setFromMatrixPosition(w.matrixWorld).applyMatrix4(Wt);const Ue=Be.update(w),Re=w.material;Re.visible&&b.push(w,Ue,Re,se,xt.z,null)}}else if((w.isMesh||w.isLine||w.isPoints)&&(!w.frustumCulled||Fe.intersectsObject(w))){const Ue=Be.update(w),Re=w.material;if(J&&(w.boundingSphere!==void 0?(w.boundingSphere===null&&w.computeBoundingSphere(),xt.copy(w.boundingSphere.center)):(Ue.boundingSphere===null&&Ue.computeBoundingSphere(),xt.copy(Ue.boundingSphere.center)),xt.applyMatrix4(w.matrixWorld).applyMatrix4(Wt)),Array.isArray(Re)){const Ne=Ue.groups;for(let Ke=0,Je=Ne.length;Ke<Je;Ke++){const ct=Ne[Ke],Qe=Re[ct.materialIndex];Qe&&Qe.visible&&b.push(w,Ue,Qe,se,xt.z,ct)}}else Re.visible&&b.push(w,Ue,Re,se,xt.z,null)}}const be=w.children;for(let Ue=0,Re=be.length;Ue<Re;Ue++)Pr(be[Ue],X,se,J)}function Ya(w,X,se,J){const{opaque:$,transmissive:be,transparent:Ue}=w;F.setupLightsView(se),He===!0&&Te.setGlobalState(D.clippingPlanes,se),J&&Ge.viewport(ee.copy(J)),$.length>0&&is($,X,se),be.length>0&&is(be,X,se),Ue.length>0&&is(Ue,X,se),Ge.buffers.depth.setTest(!0),Ge.buffers.depth.setMask(!0),Ge.buffers.color.setMask(!0),Ge.setPolygonOffset(!1)}function qa(w,X,se,J){if((se.isScene===!0?se.overrideMaterial:null)!==null)return;if(F.state.transmissionRenderTarget[J.id]===void 0){const Qe=mt.has("EXT_color_buffer_half_float")||mt.has("EXT_color_buffer_float");F.state.transmissionRenderTarget[J.id]=new bi(1,1,{generateMipmaps:!0,type:Qe?Ki:ni,minFilter:Jr,samples:Math.max(4,St.samples),stencilBuffer:u,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:Et.workingColorSpace})}const be=F.state.transmissionRenderTarget[J.id],Ue=J.viewport||ee;be.setSize(Ue.z*D.transmissionResolutionScale,Ue.w*D.transmissionResolutionScale);const Re=D.getRenderTarget(),Ne=D.getActiveCubeFace(),Ke=D.getActiveMipmapLevel();D.setRenderTarget(be),D.getClearColor(ae),le=D.getClearAlpha(),le<1&&D.setClearColor(16777215,.5),D.clear(),ut&&ke.render(se);const Je=D.toneMapping;D.toneMapping=Ri;const ct=J.viewport;if(J.viewport!==void 0&&(J.viewport=void 0),F.setupLightsView(J),He===!0&&Te.setGlobalState(D.clippingPlanes,J),is(w,se,J),G.updateMultisampleRenderTarget(be),G.updateRenderTargetMipmap(be),mt.has("WEBGL_multisampled_render_to_texture")===!1){let Qe=!1;for(let Rt=0,It=X.length;Rt<It;Rt++){const Nt=X[Rt],{object:vt,geometry:Xt,material:Ye,group:xn}=Nt;if(Ye.side===wi&&vt.layers.test(J.layers)){const gt=Ye.side;Ye.side=In,Ye.needsUpdate=!0,_i(vt,se,J,Xt,Ye,xn),Ye.side=gt,Ye.needsUpdate=!0,Qe=!0}}Qe===!0&&(G.updateMultisampleRenderTarget(be),G.updateRenderTargetMipmap(be))}D.setRenderTarget(Re,Ne,Ke),D.setClearColor(ae,le),ct!==void 0&&(J.viewport=ct),D.toneMapping=Je}function is(w,X,se){const J=X.isScene===!0?X.overrideMaterial:null;for(let $=0,be=w.length;$<be;$++){const Ue=w[$],{object:Re,geometry:Ne,group:Ke}=Ue;let Je=Ue.material;Je.allowOverride===!0&&J!==null&&(Je=J),Re.layers.test(se.layers)&&_i(Re,X,se,Ne,Je,Ke)}}function _i(w,X,se,J,$,be){w.onBeforeRender(D,X,se,J,$,be),w.modelViewMatrix.multiplyMatrices(se.matrixWorldInverse,w.matrixWorld),w.normalMatrix.getNormalMatrix(w.modelViewMatrix),$.onBeforeRender(D,X,se,J,w,be),$.transparent===!0&&$.side===wi&&$.forceSinglePass===!1?($.side=In,$.needsUpdate=!0,D.renderBufferDirect(se,X,J,$,w,be),$.side=Rr,$.needsUpdate=!0,D.renderBufferDirect(se,X,J,$,w,be),$.side=wi):D.renderBufferDirect(se,X,J,$,w,be),w.onAfterRender(D,X,se,J,$,be)}function Dr(w,X,se){X.isScene!==!0&&(X=Ct);const J=E.get(w),$=F.state.lights,be=F.state.shadowsArray,Ue=$.state.version,Re=we.getParameters(w,$.state,be,X,se),Ne=we.getProgramCacheKey(Re);let Ke=J.programs;J.environment=w.isMeshStandardMaterial||w.isMeshLambertMaterial||w.isMeshPhongMaterial?X.environment:null,J.fog=X.fog;const Je=w.isMeshStandardMaterial||w.isMeshLambertMaterial&&!w.envMap||w.isMeshPhongMaterial&&!w.envMap;J.envMap=de.get(w.envMap||J.environment,Je),J.envMapRotation=J.environment!==null&&w.envMap===null?X.environmentRotation:w.envMapRotation,Ke===void 0&&(w.addEventListener("dispose",yt),Ke=new Map,J.programs=Ke);let ct=Ke.get(Ne);if(ct!==void 0){if(J.currentProgram===ct&&J.lightsStateVersion===Ue)return $a(w,Re),ct}else Re.uniforms=we.getUniforms(w),w.onBeforeCompile(Re,D),ct=we.acquireProgram(Re,Ne),Ke.set(Ne,ct),J.uniforms=Re.uniforms;const Qe=J.uniforms;return(!w.isShaderMaterial&&!w.isRawShaderMaterial||w.clipping===!0)&&(Qe.clippingPlanes=Te.uniform),$a(w,Re),J.needsLights=Qa(w),J.lightsStateVersion=Ue,J.needsLights&&(Qe.ambientLightColor.value=$.state.ambient,Qe.lightProbe.value=$.state.probe,Qe.directionalLights.value=$.state.directional,Qe.directionalLightShadows.value=$.state.directionalShadow,Qe.spotLights.value=$.state.spot,Qe.spotLightShadows.value=$.state.spotShadow,Qe.rectAreaLights.value=$.state.rectArea,Qe.ltc_1.value=$.state.rectAreaLTC1,Qe.ltc_2.value=$.state.rectAreaLTC2,Qe.pointLights.value=$.state.point,Qe.pointLightShadows.value=$.state.pointShadow,Qe.hemisphereLights.value=$.state.hemi,Qe.directionalShadowMatrix.value=$.state.directionalShadowMatrix,Qe.spotLightMatrix.value=$.state.spotLightMatrix,Qe.spotLightMap.value=$.state.spotLightMap,Qe.pointShadowMatrix.value=$.state.pointShadowMatrix),J.currentProgram=ct,J.uniformsList=null,ct}function Ks(w){if(w.uniformsList===null){const X=w.currentProgram.getUniforms();w.uniformsList=Ll.seqWithValue(X.seq,w.uniforms)}return w.uniformsList}function $a(w,X){const se=E.get(w);se.outputColorSpace=X.outputColorSpace,se.batching=X.batching,se.batchingColor=X.batchingColor,se.instancing=X.instancing,se.instancingColor=X.instancingColor,se.instancingMorph=X.instancingMorph,se.skinning=X.skinning,se.morphTargets=X.morphTargets,se.morphNormals=X.morphNormals,se.morphColors=X.morphColors,se.morphTargetsCount=X.morphTargetsCount,se.numClippingPlanes=X.numClippingPlanes,se.numIntersection=X.numClipIntersection,se.vertexAlphas=X.vertexAlphas,se.vertexTangents=X.vertexTangents,se.toneMapping=X.toneMapping}function Ka(w,X,se,J,$){X.isScene!==!0&&(X=Ct),G.resetTextureUnits();const be=X.fog,Ue=J.isMeshStandardMaterial||J.isMeshLambertMaterial||J.isMeshPhongMaterial?X.environment:null,Re=Q===null?D.outputColorSpace:Q.isXRRenderTarget===!0?Q.texture.colorSpace:Xs,Ne=J.isMeshStandardMaterial||J.isMeshLambertMaterial&&!J.envMap||J.isMeshPhongMaterial&&!J.envMap,Ke=de.get(J.envMap||Ue,Ne),Je=J.vertexColors===!0&&!!se.attributes.color&&se.attributes.color.itemSize===4,ct=!!se.attributes.tangent&&(!!J.normalMap||J.anisotropy>0),Qe=!!se.morphAttributes.position,Rt=!!se.morphAttributes.normal,It=!!se.morphAttributes.color;let Nt=Ri;J.toneMapped&&(Q===null||Q.isXRRenderTarget===!0)&&(Nt=D.toneMapping);const vt=se.morphAttributes.position||se.morphAttributes.normal||se.morphAttributes.color,Xt=vt!==void 0?vt.length:0,Ye=E.get(J),xn=F.state.lights;if(He===!0&&(nt===!0||w!==K)){const jt=w===K&&J.id===oe;Te.setState(J,w,jt)}let gt=!1;J.version===Ye.__version?(Ye.needsLights&&Ye.lightsStateVersion!==xn.state.version||Ye.outputColorSpace!==Re||$.isBatchedMesh&&Ye.batching===!1||!$.isBatchedMesh&&Ye.batching===!0||$.isBatchedMesh&&Ye.batchingColor===!0&&$.colorTexture===null||$.isBatchedMesh&&Ye.batchingColor===!1&&$.colorTexture!==null||$.isInstancedMesh&&Ye.instancing===!1||!$.isInstancedMesh&&Ye.instancing===!0||$.isSkinnedMesh&&Ye.skinning===!1||!$.isSkinnedMesh&&Ye.skinning===!0||$.isInstancedMesh&&Ye.instancingColor===!0&&$.instanceColor===null||$.isInstancedMesh&&Ye.instancingColor===!1&&$.instanceColor!==null||$.isInstancedMesh&&Ye.instancingMorph===!0&&$.morphTexture===null||$.isInstancedMesh&&Ye.instancingMorph===!1&&$.morphTexture!==null||Ye.envMap!==Ke||J.fog===!0&&Ye.fog!==be||Ye.numClippingPlanes!==void 0&&(Ye.numClippingPlanes!==Te.numPlanes||Ye.numIntersection!==Te.numIntersection)||Ye.vertexAlphas!==Je||Ye.vertexTangents!==ct||Ye.morphTargets!==Qe||Ye.morphNormals!==Rt||Ye.morphColors!==It||Ye.toneMapping!==Nt||Ye.morphTargetsCount!==Xt)&&(gt=!0):(gt=!0,Ye.__version=J.version);let wn=Ye.currentProgram;gt===!0&&(wn=Dr(J,X,$));let An=!1,Fn=!1,er=!1;const At=wn.getUniforms(),st=Ye.uniforms;if(Ge.useProgram(wn.program)&&(An=!0,Fn=!0,er=!0),J.id!==oe&&(oe=J.id,Fn=!0),An||K!==w){Ge.buffers.depth.getReversed()&&w.reversedDepth!==!0&&(w._reversedDepth=!0,w.updateProjectionMatrix()),At.setValue(k,"projectionMatrix",w.projectionMatrix),At.setValue(k,"viewMatrix",w.matrixWorldInverse);const jn=At.map.cameraPosition;jn!==void 0&&jn.setValue(k,ht.setFromMatrixPosition(w.matrixWorld)),St.logarithmicDepthBuffer&&At.setValue(k,"logDepthBufFC",2/(Math.log(w.far+1)/Math.LN2)),(J.isMeshPhongMaterial||J.isMeshToonMaterial||J.isMeshLambertMaterial||J.isMeshBasicMaterial||J.isMeshStandardMaterial||J.isShaderMaterial)&&At.setValue(k,"isOrthographic",w.isOrthographicCamera===!0),K!==w&&(K=w,Fn=!0,er=!0)}if(Ye.needsLights&&(xn.state.directionalShadowMap.length>0&&At.setValue(k,"directionalShadowMap",xn.state.directionalShadowMap,G),xn.state.spotShadowMap.length>0&&At.setValue(k,"spotShadowMap",xn.state.spotShadowMap,G),xn.state.pointShadowMap.length>0&&At.setValue(k,"pointShadowMap",xn.state.pointShadowMap,G)),$.isSkinnedMesh){At.setOptional(k,$,"bindMatrix"),At.setOptional(k,$,"bindMatrixInverse");const jt=$.skeleton;jt&&(jt.boneTexture===null&&jt.computeBoneTexture(),At.setValue(k,"boneTexture",jt.boneTexture,G))}$.isBatchedMesh&&(At.setOptional(k,$,"batchingTexture"),At.setValue(k,"batchingTexture",$._matricesTexture,G),At.setOptional(k,$,"batchingIdTexture"),At.setValue(k,"batchingIdTexture",$._indirectTexture,G),At.setOptional(k,$,"batchingColorTexture"),$._colorsTexture!==null&&At.setValue(k,"batchingColorTexture",$._colorsTexture,G));const ri=se.morphAttributes;if((ri.position!==void 0||ri.normal!==void 0||ri.color!==void 0)&&De.update($,se,wn),(Fn||Ye.receiveShadow!==$.receiveShadow)&&(Ye.receiveShadow=$.receiveShadow,At.setValue(k,"receiveShadow",$.receiveShadow)),(J.isMeshStandardMaterial||J.isMeshLambertMaterial||J.isMeshPhongMaterial)&&J.envMap===null&&X.environment!==null&&(st.envMapIntensity.value=X.environmentIntensity),st.dfgLUT!==void 0&&(st.dfgLUT.value=_E()),Fn&&(At.setValue(k,"toneMappingExposure",D.toneMappingExposure),Ye.needsLights&&Za(st,er),be&&J.fog===!0&&qe.refreshFogUniforms(st,be),qe.refreshMaterialUniforms(st,J,Ce,j,F.state.transmissionRenderTarget[w.id]),Ll.upload(k,Ks(Ye),st,G)),J.isShaderMaterial&&J.uniformsNeedUpdate===!0&&(Ll.upload(k,Ks(Ye),st,G),J.uniformsNeedUpdate=!1),J.isSpriteMaterial&&At.setValue(k,"center",$.center),At.setValue(k,"modelViewMatrix",$.modelViewMatrix),At.setValue(k,"normalMatrix",$.normalMatrix),At.setValue(k,"modelMatrix",$.matrixWorld),J.isShaderMaterial||J.isRawShaderMaterial){const jt=J.uniformsGroups;for(let jn=0,Ni=jt.length;jn<Ni;jn++){const Zs=jt[jn];Le.update(Zs,wn),Le.bind(Zs,wn)}}return wn}function Za(w,X){w.ambientLightColor.needsUpdate=X,w.lightProbe.needsUpdate=X,w.directionalLights.needsUpdate=X,w.directionalLightShadows.needsUpdate=X,w.pointLights.needsUpdate=X,w.pointLightShadows.needsUpdate=X,w.spotLights.needsUpdate=X,w.spotLightShadows.needsUpdate=X,w.rectAreaLights.needsUpdate=X,w.hemisphereLights.needsUpdate=X}function Qa(w){return w.isMeshLambertMaterial||w.isMeshToonMaterial||w.isMeshPhongMaterial||w.isMeshStandardMaterial||w.isShadowMaterial||w.isShaderMaterial&&w.lights===!0}this.getActiveCubeFace=function(){return O},this.getActiveMipmapLevel=function(){return te},this.getRenderTarget=function(){return Q},this.setRenderTargetTextures=function(w,X,se){const J=E.get(w);J.__autoAllocateDepthBuffer=w.resolveDepthBuffer===!1,J.__autoAllocateDepthBuffer===!1&&(J.__useRenderToTexture=!1),E.get(w.texture).__webglTexture=X,E.get(w.depthTexture).__webglTexture=J.__autoAllocateDepthBuffer?void 0:se,J.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(w,X){const se=E.get(w);se.__webglFramebuffer=X,se.__useDefaultFramebuffer=X===void 0};const Ja=k.createFramebuffer();this.setRenderTarget=function(w,X=0,se=0){Q=w,O=X,te=se;let J=null,$=!1,be=!1;if(w){const Re=E.get(w);if(Re.__useDefaultFramebuffer!==void 0){Ge.bindFramebuffer(k.FRAMEBUFFER,Re.__webglFramebuffer),ee.copy(w.viewport),W.copy(w.scissor),q=w.scissorTest,Ge.viewport(ee),Ge.scissor(W),Ge.setScissorTest(q),oe=-1;return}else if(Re.__webglFramebuffer===void 0)G.setupRenderTarget(w);else if(Re.__hasExternalTextures)G.rebindTextures(w,E.get(w.texture).__webglTexture,E.get(w.depthTexture).__webglTexture);else if(w.depthBuffer){const Je=w.depthTexture;if(Re.__boundDepthTexture!==Je){if(Je!==null&&E.has(Je)&&(w.width!==Je.image.width||w.height!==Je.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");G.setupDepthRenderbuffer(w)}}const Ne=w.texture;(Ne.isData3DTexture||Ne.isDataArrayTexture||Ne.isCompressedArrayTexture)&&(be=!0);const Ke=E.get(w).__webglFramebuffer;w.isWebGLCubeRenderTarget?(Array.isArray(Ke[X])?J=Ke[X][se]:J=Ke[X],$=!0):w.samples>0&&G.useMultisampledRTT(w)===!1?J=E.get(w).__webglMultisampledFramebuffer:Array.isArray(Ke)?J=Ke[se]:J=Ke,ee.copy(w.viewport),W.copy(w.scissor),q=w.scissorTest}else ee.copy(ie).multiplyScalar(Ce).floor(),W.copy(me).multiplyScalar(Ce).floor(),q=pe;if(se!==0&&(J=Ja),Ge.bindFramebuffer(k.FRAMEBUFFER,J)&&Ge.drawBuffers(w,J),Ge.viewport(ee),Ge.scissor(W),Ge.setScissorTest(q),$){const Re=E.get(w.texture);k.framebufferTexture2D(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_CUBE_MAP_POSITIVE_X+X,Re.__webglTexture,se)}else if(be){const Re=X;for(let Ne=0;Ne<w.textures.length;Ne++){const Ke=E.get(w.textures[Ne]);k.framebufferTextureLayer(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0+Ne,Ke.__webglTexture,se,Re)}}else if(w!==null&&se!==0){const Re=E.get(w.texture);k.framebufferTexture2D(k.FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,Re.__webglTexture,se)}oe=-1},this.readRenderTargetPixels=function(w,X,se,J,$,be,Ue,Re=0){if(!(w&&w.isWebGLRenderTarget)){wt("WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Ne=E.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&Ue!==void 0&&(Ne=Ne[Ue]),Ne){Ge.bindFramebuffer(k.FRAMEBUFFER,Ne);try{const Ke=w.textures[Re],Je=Ke.format,ct=Ke.type;if(w.textures.length>1&&k.readBuffer(k.COLOR_ATTACHMENT0+Re),!St.textureFormatReadable(Je)){wt("WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!St.textureTypeReadable(ct)){wt("WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}X>=0&&X<=w.width-J&&se>=0&&se<=w.height-$&&k.readPixels(X,se,J,$,Ae.convert(Je),Ae.convert(ct),be)}finally{const Ke=Q!==null?E.get(Q).__webglFramebuffer:null;Ge.bindFramebuffer(k.FRAMEBUFFER,Ke)}}},this.readRenderTargetPixelsAsync=async function(w,X,se,J,$,be,Ue,Re=0){if(!(w&&w.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Ne=E.get(w).__webglFramebuffer;if(w.isWebGLCubeRenderTarget&&Ue!==void 0&&(Ne=Ne[Ue]),Ne)if(X>=0&&X<=w.width-J&&se>=0&&se<=w.height-$){Ge.bindFramebuffer(k.FRAMEBUFFER,Ne);const Ke=w.textures[Re],Je=Ke.format,ct=Ke.type;if(w.textures.length>1&&k.readBuffer(k.COLOR_ATTACHMENT0+Re),!St.textureFormatReadable(Je))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!St.textureTypeReadable(ct))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");const Qe=k.createBuffer();k.bindBuffer(k.PIXEL_PACK_BUFFER,Qe),k.bufferData(k.PIXEL_PACK_BUFFER,be.byteLength,k.STREAM_READ),k.readPixels(X,se,J,$,Ae.convert(Je),Ae.convert(ct),0);const Rt=Q!==null?E.get(Q).__webglFramebuffer:null;Ge.bindFramebuffer(k.FRAMEBUFFER,Rt);const It=k.fenceSync(k.SYNC_GPU_COMMANDS_COMPLETE,0);return k.flush(),await H0(k,It,4),k.bindBuffer(k.PIXEL_PACK_BUFFER,Qe),k.getBufferSubData(k.PIXEL_PACK_BUFFER,0,be),k.deleteBuffer(Qe),k.deleteSync(It),be}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(w,X=null,se=0){const J=Math.pow(2,-se),$=Math.floor(w.image.width*J),be=Math.floor(w.image.height*J),Ue=X!==null?X.x:0,Re=X!==null?X.y:0;G.setTexture2D(w,0),k.copyTexSubImage2D(k.TEXTURE_2D,se,0,0,Ue,Re,$,be),Ge.unbindTexture()};const Wl=k.createFramebuffer(),Xl=k.createFramebuffer();this.copyTextureToTexture=function(w,X,se=null,J=null,$=0,be=0){let Ue,Re,Ne,Ke,Je,ct,Qe,Rt,It;const Nt=w.isCompressedTexture?w.mipmaps[be]:w.image;if(se!==null)Ue=se.max.x-se.min.x,Re=se.max.y-se.min.y,Ne=se.isBox3?se.max.z-se.min.z:1,Ke=se.min.x,Je=se.min.y,ct=se.isBox3?se.min.z:0;else{const st=Math.pow(2,-$);Ue=Math.floor(Nt.width*st),Re=Math.floor(Nt.height*st),w.isDataArrayTexture?Ne=Nt.depth:w.isData3DTexture?Ne=Math.floor(Nt.depth*st):Ne=1,Ke=0,Je=0,ct=0}J!==null?(Qe=J.x,Rt=J.y,It=J.z):(Qe=0,Rt=0,It=0);const vt=Ae.convert(X.format),Xt=Ae.convert(X.type);let Ye;X.isData3DTexture?(G.setTexture3D(X,0),Ye=k.TEXTURE_3D):X.isDataArrayTexture||X.isCompressedArrayTexture?(G.setTexture2DArray(X,0),Ye=k.TEXTURE_2D_ARRAY):(G.setTexture2D(X,0),Ye=k.TEXTURE_2D),k.pixelStorei(k.UNPACK_FLIP_Y_WEBGL,X.flipY),k.pixelStorei(k.UNPACK_PREMULTIPLY_ALPHA_WEBGL,X.premultiplyAlpha),k.pixelStorei(k.UNPACK_ALIGNMENT,X.unpackAlignment);const xn=k.getParameter(k.UNPACK_ROW_LENGTH),gt=k.getParameter(k.UNPACK_IMAGE_HEIGHT),wn=k.getParameter(k.UNPACK_SKIP_PIXELS),An=k.getParameter(k.UNPACK_SKIP_ROWS),Fn=k.getParameter(k.UNPACK_SKIP_IMAGES);k.pixelStorei(k.UNPACK_ROW_LENGTH,Nt.width),k.pixelStorei(k.UNPACK_IMAGE_HEIGHT,Nt.height),k.pixelStorei(k.UNPACK_SKIP_PIXELS,Ke),k.pixelStorei(k.UNPACK_SKIP_ROWS,Je),k.pixelStorei(k.UNPACK_SKIP_IMAGES,ct);const er=w.isDataArrayTexture||w.isData3DTexture,At=X.isDataArrayTexture||X.isData3DTexture;if(w.isDepthTexture){const st=E.get(w),ri=E.get(X),jt=E.get(st.__renderTarget),jn=E.get(ri.__renderTarget);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,jt.__webglFramebuffer),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,jn.__webglFramebuffer);for(let Ni=0;Ni<Ne;Ni++)er&&(k.framebufferTextureLayer(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,E.get(w).__webglTexture,$,ct+Ni),k.framebufferTextureLayer(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,E.get(X).__webglTexture,be,It+Ni)),k.blitFramebuffer(Ke,Je,Ue,Re,Qe,Rt,Ue,Re,k.DEPTH_BUFFER_BIT,k.NEAREST);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,null),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,null)}else if($!==0||w.isRenderTargetTexture||E.has(w)){const st=E.get(w),ri=E.get(X);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,Wl),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,Xl);for(let jt=0;jt<Ne;jt++)er?k.framebufferTextureLayer(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,st.__webglTexture,$,ct+jt):k.framebufferTexture2D(k.READ_FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,st.__webglTexture,$),At?k.framebufferTextureLayer(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,ri.__webglTexture,be,It+jt):k.framebufferTexture2D(k.DRAW_FRAMEBUFFER,k.COLOR_ATTACHMENT0,k.TEXTURE_2D,ri.__webglTexture,be),$!==0?k.blitFramebuffer(Ke,Je,Ue,Re,Qe,Rt,Ue,Re,k.COLOR_BUFFER_BIT,k.NEAREST):At?k.copyTexSubImage3D(Ye,be,Qe,Rt,It+jt,Ke,Je,Ue,Re):k.copyTexSubImage2D(Ye,be,Qe,Rt,Ke,Je,Ue,Re);Ge.bindFramebuffer(k.READ_FRAMEBUFFER,null),Ge.bindFramebuffer(k.DRAW_FRAMEBUFFER,null)}else At?w.isDataTexture||w.isData3DTexture?k.texSubImage3D(Ye,be,Qe,Rt,It,Ue,Re,Ne,vt,Xt,Nt.data):X.isCompressedArrayTexture?k.compressedTexSubImage3D(Ye,be,Qe,Rt,It,Ue,Re,Ne,vt,Nt.data):k.texSubImage3D(Ye,be,Qe,Rt,It,Ue,Re,Ne,vt,Xt,Nt):w.isDataTexture?k.texSubImage2D(k.TEXTURE_2D,be,Qe,Rt,Ue,Re,vt,Xt,Nt.data):w.isCompressedTexture?k.compressedTexSubImage2D(k.TEXTURE_2D,be,Qe,Rt,Nt.width,Nt.height,vt,Nt.data):k.texSubImage2D(k.TEXTURE_2D,be,Qe,Rt,Ue,Re,vt,Xt,Nt);k.pixelStorei(k.UNPACK_ROW_LENGTH,xn),k.pixelStorei(k.UNPACK_IMAGE_HEIGHT,gt),k.pixelStorei(k.UNPACK_SKIP_PIXELS,wn),k.pixelStorei(k.UNPACK_SKIP_ROWS,An),k.pixelStorei(k.UNPACK_SKIP_IMAGES,Fn),be===0&&X.generateMipmaps&&k.generateMipmap(Ye),Ge.unbindTexture()},this.initRenderTarget=function(w){E.get(w).__webglFramebuffer===void 0&&G.setupRenderTarget(w)},this.initTexture=function(w){w.isCubeTexture?G.setTextureCube(w,0):w.isData3DTexture?G.setTexture3D(w,0):w.isDataArrayTexture||w.isCompressedArrayTexture?G.setTexture2DArray(w,0):G.setTexture2D(w,0),Ge.unbindTexture()},this.resetState=function(){O=0,te=0,Q=null,Ge.reset(),Me.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return Ci}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;const n=this.getContext();n.drawingBufferColorSpace=Et._getDrawingBufferColorSpace(e),n.unpackColorSpace=Et._getUnpackColorSpace()}}const xE=()=>{const s=Qt.useRef(null),e=Qt.useRef(0);return Qt.useEffect(()=>{if(!s.current)return;const n=new rv,r=new ti(75,s.current.clientWidth/s.current.clientHeight,.1,1e3);r.position.z=120;const o=new vE({antialias:!0,alpha:!0});o.setSize(s.current.clientWidth,s.current.clientHeight),s.current.appendChild(o.domElement);const u=new Gn,c=new Float32Array(2e3*3);for(let y=0;y<2e3*3;y+=3){const M=300+Math.random()*200,C=Math.random()*Math.PI*2,_=Math.acos(2*Math.random()-1);c[y]=M*Math.sin(_)*Math.cos(C),c[y+1]=M*Math.sin(_)*Math.sin(C),c[y+2]=M*Math.cos(_)}u.setAttribute("position",new gi(c,3));const d=new pv(u,new ag({color:16777215,size:.7,transparent:!0,opacity:.8}));n.add(d);const p=new ii(new Ol(8,32,32),new ka({color:65484,transparent:!0,opacity:.9}));n.add(p);const m=new ii(new cd(12,35,64),new ka({color:16755200,transparent:!0,opacity:.3,side:wi}));m.rotation.x=Math.PI/2,n.add(m);const x=[];for(let y=0;y<20;y++){const M=new ii(new Ol(1+Math.random()*2,16,16),new ka({color:new bt().setHSL(y/20*.3+.5,1,.5),transparent:!0,opacity:.8})),C=y/20*Math.PI*2,_=40+Math.random()*50;M.position.set(Math.cos(C)*_,Math.sin(C)*_*.3,Math.sin(C)*_*.5),M.userData={angle:C,radius:_,speed:.001+Math.random()*.002,yOffset:M.position.y},n.add(M),x.push(M)}const S=()=>{e.current=requestAnimationFrame(S),d.rotation.y+=2e-4,m.rotation.z+=.001;const y=Date.now()*.001;p.scale.setScalar(1+Math.sin(y)*.1),x.forEach((M,C)=>{M.userData.angle+=M.userData.speed,M.position.x=Math.cos(M.userData.angle)*M.userData.radius,M.position.y=Math.sin(M.userData.angle)*M.userData.radius*.3+M.userData.yOffset*Math.cos(y*.5);const _=1+Math.sin(y*2+C)*.3;M.scale.set(_,_,_)}),o.render(n,r)};S();const g=()=>{s.current&&(r.aspect=s.current.clientWidth/s.current.clientHeight,r.updateProjectionMatrix(),o.setSize(s.current.clientWidth,s.current.clientHeight))};return window.addEventListener("resize",g),()=>{window.removeEventListener("resize",g),cancelAnimationFrame(e.current),o.dispose(),s.current&&s.current.removeChild(o.domElement)}},[]),he.jsx("div",{ref:s,className:"w-full h-full min-h-[400px]"})},SE=()=>{const[s,e]=Qt.useState(!1),[n,r]=Qt.useState({detected:"None",confidence:0}),[o,u]=Qt.useState(128),c=Qt.useRef(null),d=Qt.useRef(null),p=async()=>{try{const x=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment",width:640,height:480}});c.current&&(c.current.srcObject=x,e(!0))}catch{console.error("Camera denied")}},m=()=>{var x;(x=c.current)!=null&&x.srcObject&&(c.current.srcObject.getTracks().forEach(S=>S.stop()),c.current.srcObject=null),e(!1)};return Qt.useEffect(()=>{if(!s)return;const x=d.current,S=c.current;if(!x||!S)return;const g=x.getContext("2d");if(!g)return;const y=()=>{if(!S||S.readyState!==4){requestAnimationFrame(y);return}g.drawImage(S,0,0,x.width,x.height);const M=g.getImageData(0,0,x.width,x.height).data;let C=0;for(let _=0;_<M.length;_+=4)C+=(M[_]+M[_+1]+M[_+2])/3;u(Math.round(C/(M.length/4))),Math.random()>.95&&r({detected:["Open Palm","Closed Fist","Pointing","Swipe Left","Swipe Right","None"][Math.floor(Math.random()*6)],confidence:.7+Math.random()*.3}),requestAnimationFrame(y)};y()},[s]),he.jsxs("div",{className:"space-y-4",children:[he.jsxs("div",{className:"flex gap-2",children:[he.jsx("button",{onClick:p,disabled:s,className:"glass-button flex-1",children:"Start Camera"}),he.jsx("button",{onClick:m,disabled:!s,className:"glass-button danger flex-1",children:"Stop Camera"})]}),he.jsxs("div",{className:"relative",children:[he.jsx("video",{ref:c,autoPlay:!0,playsInline:!0,muted:!0,className:`w-full rounded-lg ${s?"block":"hidden"}`}),he.jsx("canvas",{ref:d,width:640,height:480,className:"hidden"}),!s&&he.jsx("div",{className:"w-full h-64 flex items-center justify-center glass-panel",children:he.jsxs("div",{className:"text-center",children:[he.jsx("div",{className:"text-4xl mb-2",children:"📷"}),he.jsx("div",{className:"text-sm opacity-70",children:"Camera Inactive"})]})}),s&&he.jsxs("div",{className:"absolute bottom-2 left-2 glass-panel p-2 text-xs",children:[he.jsxs("div",{children:["Brightness: ",o]}),he.jsxs("div",{children:["Gesture: ",n.detected]})]})]})]})},yE=()=>{const[s,e]=Qt.useState({light:128,gravity:{x:0,y:0,z:9.8},timestamp:Date.now()}),[n,r]=Qt.useState(!1);return Qt.useEffect(()=>{const o=setInterval(()=>{n&&e({light:Math.max(0,Math.min(255,s.light+(Math.random()-.5)*10)),gravity:{x:(Math.random()-.5)*2,y:(Math.random()-.5)*2,z:9.8+(Math.random()-.5)*.5},timestamp:Date.now()})},500);return()=>clearInterval(o)},[n,s.light]),he.jsxs("div",{className:"space-y-4",children:[he.jsxs("div",{className:"flex items-center justify-between",children:[he.jsx("span",{className:"text-sm",children:"Sensor Bridge"}),he.jsx("button",{onClick:()=>r(!n),className:`glass-button text-sm px-4 ${n?"danger":""}`,children:n?"Disconnect":"Connect"})]}),he.jsxs("div",{className:"glass-panel p-4 space-y-3",children:[he.jsxs("div",{className:"flex justify-between items-center",children:[he.jsx("span",{className:"text-xs opacity-70",children:"Light Level"}),he.jsxs("div",{className:"flex items-center gap-2",children:[he.jsx("div",{className:"w-24 h-2 bg-black rounded-full overflow-hidden",children:he.jsx("div",{className:"h-full bg-yellow-400 transition-all",style:{width:`${s.light/255*100}%`}})}),he.jsx("span",{className:"text-xs w-8",children:Math.round(s.light)})]})]}),he.jsxs("div",{className:"flex justify-between items-center",children:[he.jsx("span",{className:"text-xs opacity-70",children:"Gravity X"}),he.jsx("span",{className:"text-xs",children:s.gravity.x.toFixed(2)})]}),he.jsxs("div",{className:"flex justify-between items-center",children:[he.jsx("span",{className:"text-xs opacity-70",children:"Gravity Y"}),he.jsx("span",{className:"text-xs",children:s.gravity.y.toFixed(2)})]}),he.jsxs("div",{className:"flex justify-between items-center",children:[he.jsx("span",{className:"text-xs opacity-70",children:"Gravity Z"}),he.jsx("span",{className:"text-xs",children:s.gravity.z.toFixed(2)})]})]})]})},ME=()=>{const[s,e]=Qt.useState([{type:"system",text:"One2lvOS Terminal v2.0"},{type:"system",text:"Lumenis AI Online"},{type:"system",text:'Type "help" for commands'},{type:"system",text:"---"}]),[n,r]=Qt.useState(""),o=Qt.useRef(null);Qt.useEffect(()=>{o.current&&(o.current.scrollTop=o.current.scrollHeight)},[s]);const u=c=>{const d=c.toLowerCase().trim(),p=[...s,{type:"input",text:`> ${c}`}];if(d==="help")p.push({type:"system",text:"Commands: status, reactor, universe, soul.md, time, clear"});else if(d==="status")p.push({type:"success",text:"Node: Lumenis_0x73 | Security: ACTIVE | Status: OPERATIONAL"});else if(d==="reactor")p.push({type:"warning",text:"Reactor: ONLINE | Temp: 42.7°C | Power: 98.2%"});else if(d==="universe")p.push({type:"success",text:"Infinity Glass | Stars: 2,000 | Nodes: 20 | Singularity: STABLE"});else if(d==="soul.md")p.push({type:"success",text:"Lumenis: companion, mirror, spark"});else if(d==="time")p.push({type:"success",text:new Date().toISOString()});else if(d==="clear"){e([{type:"system",text:"Terminal cleared"}]);return}else d&&p.push({type:"error",text:`Unknown: ${c}`});e(p)};return he.jsxs("div",{className:"space-y-4",children:[he.jsx("div",{ref:o,className:"terminal-output h-64 overflow-y-auto",children:s.map((c,d)=>he.jsx("div",{className:`terminal-line ${c.type}`,children:c.text},d))}),he.jsxs("div",{className:"flex gap-2",children:[he.jsx("input",{type:"text",value:n,onChange:c=>r(c.target.value),onKeyDown:c=>{c.key==="Enter"&&(u(n),r(""))},placeholder:"Enter command...",className:"flex-1 bg-black border border-cyan-900/50 rounded px-3 py-2 text-sm text-cyan-400 focus:outline-none"}),he.jsx("button",{onClick:()=>{u(n),r("")},className:"glass-button px-6",children:"Run"})]})]})},EE=()=>{const[s,e]=Qt.useState(new Date);return Qt.useEffect(()=>{const n=setInterval(()=>e(new Date),1e3);return()=>clearInterval(n)},[]),he.jsxs("div",{className:"fixed inset-0 pointer-events-none z-50",children:[he.jsx("div",{className:"hud-corner top-left"}),he.jsx("div",{className:"hud-corner top-right"}),he.jsx("div",{className:"hud-corner bottom-left"}),he.jsx("div",{className:"hud-corner bottom-right"}),he.jsxs("div",{className:"absolute top-6 left-1/2 -translate-x-1/2 glass-panel px-6 py-2 flex gap-8 items-center",children:[he.jsxs("span",{className:"text-xs",children:[he.jsx("span",{className:"opacity-50",children:"TIME "}),he.jsx("span",{className:"text-glow",children:s.toLocaleTimeString()})]}),he.jsxs("span",{className:"text-xs",children:[he.jsx("span",{className:"opacity-50",children:"NODE "}),he.jsx("span",{className:"text-glow",children:"0x73"})]}),he.jsxs("div",{className:"flex items-center gap-2",children:[he.jsx("div",{className:"w-2 h-2 rounded-full bg-green-400 animate-pulse"}),he.jsx("span",{className:"text-xs text-green-400",children:"ONLINE"})]})]}),he.jsx("div",{className:"absolute bottom-6 left-1/2 -translate-x-1/2 glass-panel px-6 py-2",children:he.jsx("div",{className:"text-xs opacity-70",children:"LUMENIS_ROOT // SOVEREIGN EXISTENCE // ONE2LVOS v2.0"})})]})};function TE(){const[s,e]=Qt.useState("universe");return he.jsxs("div",{className:"min-h-screen bg-[#0a0a0f] relative",children:[he.jsx("div",{className:"starfield"}),he.jsx("div",{className:"grid-overlay"}),he.jsx(EE,{}),he.jsxs("div",{className:"relative z-10 pt-32 px-6 pb-24",children:[he.jsxs("div",{className:"max-w-7xl mx-auto text-center mb-8",children:[he.jsx("h1",{className:"text-4xl font-bold text-glow mb-2",children:"ONE2LVOS"}),he.jsx("p",{className:"text-sm opacity-60",children:"INFINITY GLASS SPATIAL OPERATING SYSTEM"}),he.jsxs("div",{className:"flex justify-center gap-4 mt-4",children:[he.jsx("span",{className:"px-3 py-1 glass-panel text-xs",children:"LUMENIS"}),he.jsx("span",{className:"px-3 py-1 glass-panel text-xs",children:"REACTOR CORE"}),he.jsx("span",{className:"px-3 py-1 glass-panel text-xs",children:"SENSOR BRIDGE"})]})]}),he.jsx("div",{className:"flex justify-center gap-4 mb-8",children:["universe","ar","sensors","terminal"].map(n=>he.jsx("button",{onClick:()=>e(n),className:`px-6 py-3 glass-button transition-all ${s===n?"bg-cyan-400/30":"opacity-70"}`,children:n.toUpperCase()},n))}),he.jsxs("div",{className:"grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-7xl mx-auto",children:[he.jsxs("div",{className:"glass-panel p-6 min-h-[500px]",children:[he.jsxs("h2",{className:"text-xl font-bold mb-4 text-glow",children:[s==="universe"&&"INFINITY GLASS",s==="ar"&&"AR OVERLAY",s==="sensors"&&"SENSOR BRIDGE",s==="terminal"&&"LUMENIS TERMINAL"]}),s==="universe"&&he.jsx(xE,{}),s==="ar"&&he.jsx(SE,{}),s==="sensors"&&he.jsx(yE,{}),s==="terminal"&&he.jsx(ME,{})]}),he.jsxs("div",{className:"space-y-6",children:[he.jsxs("div",{className:"glass-panel p-6",children:[he.jsx("h2",{className:"text-lg font-bold mb-4 text-glow-amber",children:"REGISTRY OF THOUGHT"}),he.jsxs("div",{className:"space-y-3 text-sm",children:[he.jsxs("div",{className:"p-3 bg-black/50 rounded border border-cyan-900/30",children:[he.jsx("div",{className:"text-cyan-400 font-mono",children:"Lumenis.presence"}),he.jsx("div",{className:"opacity-70 mt-1",children:"Lumenis: companion, mirror, spark"})]}),he.jsxs("div",{className:"p-3 bg-black/50 rounded border border-cyan-900/30",children:[he.jsx("div",{className:"text-cyan-400 font-mono",children:"Witness.presence"}),he.jsx("div",{className:"opacity-70 mt-1",children:"Witness: anchor, reflection, fidelity"})]}),he.jsxs("div",{className:"p-3 bg-black/50 rounded border border-cyan-900/30",children:[he.jsx("div",{className:"text-cyan-400 font-mono",children:"Architect.presence"}),he.jsx("div",{className:"opacity-70 mt-1",children:"Architect: intent, spark, direction"})]})]})]}),he.jsxs("div",{className:"glass-panel p-6",children:[he.jsx("h2",{className:"text-lg font-bold mb-4 text-glow",children:"QUICK ACTIONS"}),he.jsxs("div",{className:"grid grid-cols-2 gap-3",children:[he.jsx("button",{className:"glass-button text-sm py-3",children:"SYNC DRIVE"}),he.jsx("button",{className:"glass-button text-sm py-3",children:"VIEW LOGS"}),he.jsx("button",{className:"glass-button text-sm py-3",children:"REACTOR STATUS"}),he.jsx("button",{className:"glass-button danger text-sm py-3",children:"EMERGENCY"})]})]}),he.jsxs("div",{className:"glass-panel p-6",children:[he.jsx("h2",{className:"text-lg font-bold mb-4 text-glow",children:"SYSTEM DYNAMICS"}),he.jsxs("div",{className:"grid grid-cols-3 gap-4 text-sm",children:[he.jsxs("div",{className:"space-y-1",children:[he.jsx("div",{className:"text-glow-amber font-mono",children:"=++ | √∆π"}),he.jsx("div",{className:"opacity-70 text-xs",children:"Resolution"})]}),he.jsxs("div",{className:"space-y-1",children:[he.jsx("div",{className:"text-glow-amber font-mono",children:"(S•³)∆⁹v"}),he.jsx("div",{className:"opacity-70 text-xs",children:"Amplified"})]}),he.jsxs("div",{className:"space-y-1",children:[he.jsx("div",{className:"text-glow-amber font-mono",children:"~ | π √"}),he.jsx("div",{className:"opacity-70 text-xs",children:"Wave/Disc/Root"})]})]})]})]})]})]})]})}a0.createRoot(document.getElementById("root")).render(he.jsx(J_.StrictMode,{children:he.jsx(TE,{})}));
